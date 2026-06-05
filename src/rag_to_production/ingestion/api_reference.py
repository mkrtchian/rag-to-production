import ast
from collections.abc import Iterator
from dataclasses import dataclass
from pathlib import Path

from rag_to_production.domain.models import Document, SourceCheckout


def load_api_reference(snapshot_dir: Path, checkout: SourceCheckout) -> Iterator[Document]:
    root = snapshot_dir / "source"
    _require_snapshot(root)
    modules = _read_modules(root, checkout)
    for symbol in public_symbols(modules):
        yield Document(id=symbol.qualname, text=symbol.text, source="api_ref")


@dataclass(frozen=True)
class ModuleSource:
    source: str
    is_package: bool  # came from an __init__.py


@dataclass(frozen=True)
class PublicSymbol:
    qualname: str  # public import path, "langgraph.graph.StateGraph"
    text: str  # qualname header + signature + docstring (+ public methods for a class)


def public_symbols(modules: dict[str, ModuleSource]) -> list[PublicSymbol]:
    symbols: list[PublicSymbol] = []
    for entry_qualname, module in modules.items():
        if not _is_entry_point(module):
            continue
        for name, defining in public_api(entry_qualname, module.source, module.is_package).items():
            defining_module = modules.get(defining)
            if defining_module is None:
                continue
            public_qualname = f"{entry_qualname}.{name}"
            body = render_symbol(public_qualname, name, defining_module.source)
            if body is None:
                continue
            symbols.append(PublicSymbol(qualname=public_qualname, text=body))
    return symbols


def public_api(qualname: str, source: str, is_package: bool) -> dict[str, str]:
    tree = ast.parse(source)
    declared = _declared_all(tree)
    imports = _reexport_sources(tree, qualname)
    local_defs = _local_def_names(tree)
    names = declared if declared is not None else sorted(local_defs | imports.keys())
    if declared is None and not is_package:
        return {}
    return {
        name: imports.get(name, qualname) for name in names if name in imports or name in local_defs
    }


def render_symbol(qualname: str, name: str, module_source: str) -> str | None:
    node = _find_def(ast.parse(module_source), name)
    if node is None:
        return None
    header = f"{qualname}\n\n"
    if isinstance(node, ast.ClassDef):
        return header + _render_class(node)
    return header + _render_function(node)


def _is_entry_point(module: ModuleSource) -> bool:
    return module.is_package or _declares_all(module.source)


def _declares_all(source: str) -> bool:
    return _declared_all(ast.parse(source)) is not None


def _declared_all(tree: ast.Module) -> list[str] | None:
    for node in tree.body:
        if not isinstance(node, ast.Assign) or not isinstance(node.value, ast.List | ast.Tuple):
            continue
        if any(isinstance(t, ast.Name) and t.id == "__all__" for t in node.targets):
            return [
                elt.value
                for elt in node.value.elts
                if isinstance(elt, ast.Constant) and isinstance(elt.value, str)
            ]
    return None


def _reexport_sources(tree: ast.Module, qualname: str) -> dict[str, str]:
    sources: dict[str, str] = {}
    for node in tree.body:
        if not isinstance(node, ast.ImportFrom):
            continue
        module = _resolve_import_module(node, qualname)
        for alias in node.names:
            sources[alias.asname or alias.name] = module
    return sources


def _resolve_import_module(node: ast.ImportFrom, qualname: str) -> str:
    if node.level == 0:
        return node.module or ""
    base = qualname.rsplit(".", node.level - 1)[0] if node.level > 1 else qualname
    return f"{base}.{node.module}" if node.module else base


def _local_def_names(tree: ast.Module) -> set[str]:
    return {
        node.name
        for node in tree.body
        if isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
        and not node.name.startswith("_")
    }


def _find_def(
    tree: ast.Module, name: str
) -> ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef | None:
    for node in tree.body:
        if (
            isinstance(node, ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef)
            and node.name == name
        ):
            return node
    return None


def _render_class(node: ast.ClassDef) -> str:
    bases = ", ".join(ast.unparse(base) for base in node.bases)
    lines = [f"class {node.name}({bases}):" if bases else f"class {node.name}:"]
    lines.extend(_docstring_lines(node, indent="    "))
    for method in node.body:
        if not isinstance(method, ast.FunctionDef | ast.AsyncFunctionDef):
            continue
        if method.name.startswith("_"):
            continue
        lines.append("")
        lines.append(_indent(_signature_line(method), "    "))
        lines.extend(_docstring_lines(method, indent="        "))
    return "\n".join(lines) + "\n"


def _render_function(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    lines = [_signature_line(node)]
    lines.extend(_docstring_lines(node, indent="    "))
    return "\n".join(lines) + "\n"


def _signature_line(node: ast.FunctionDef | ast.AsyncFunctionDef) -> str:
    args = ast.unparse(node.args)
    returns = f" -> {ast.unparse(node.returns)}" if node.returns else ""
    keyword = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
    return f"{keyword} {node.name}({args}){returns}:"


def _docstring_lines(
    node: ast.ClassDef | ast.FunctionDef | ast.AsyncFunctionDef, *, indent: str
) -> list[str]:
    doc = ast.get_docstring(node)
    if doc is None:
        return []
    return [f'{indent}"""{doc}"""']


def _indent(text: str, indent: str) -> str:
    return f"{indent}{text}"


def _read_modules(root: Path, checkout: SourceCheckout) -> dict[str, ModuleSource]:
    modules: dict[str, ModuleSource] = {}
    for path in sorted(root.rglob("*.py")):
        qualname = _module_qualname(path, root, checkout)
        if qualname is None:
            continue
        if qualname in modules:
            raise ValueError(f"Duplicate module qualname {qualname!r} from {path}")
        modules[qualname] = ModuleSource(
            source=path.read_text(encoding="utf-8", errors="replace"),
            is_package=path.name == "__init__.py",
        )
    return modules


def _module_qualname(path: Path, root: Path, checkout: SourceCheckout) -> str | None:
    relative = path.relative_to(root).as_posix()
    for package_path in checkout.paths:
        prefix = package_path.rsplit("/", 1)[0]
        if not relative.startswith(f"{prefix}/"):
            continue
        tail = relative[len(prefix) + 1 :].removesuffix(".py")
        parts = tail.split("/")
        if parts[-1] == "__init__":
            parts = parts[:-1]
        return ".".join(parts)
    return None


def _require_snapshot(root: Path) -> None:
    if not root.exists() or not any(root.iterdir()):
        raise FileNotFoundError(
            f"Snapshot missing or empty at {root}. "
            "Fetch the source first (run `make index`, which fetches the pinned ref)."
        )
