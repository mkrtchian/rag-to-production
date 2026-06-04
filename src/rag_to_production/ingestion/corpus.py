from collections.abc import Iterator
from pathlib import Path

from rag_to_production.domain.models import Document

_DOC_SUFFIXES = (".mdx", ".md")


def load_docs(snapshot_dir: Path) -> Iterator[Document]:
    docs_root = snapshot_dir / "docs"
    _require_snapshot(docs_root)
    yield from _documents_under(docs_root, source="docs")


def load_api_reference(snapshot_dir: Path) -> Iterator[Document]:
    langgraph_root = snapshot_dir / "langgraph"
    _require_snapshot(langgraph_root)
    yield from _documents_under(langgraph_root / "docs", source="api_ref")


def _documents_under(root: Path, source: str) -> Iterator[Document]:
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in _DOC_SUFFIXES or not path.is_file():
            continue
        # mdx is treated as plain text: frontmatter and code fences are not
        # parsed out (naive baseline, a named chunking limit).
        text = path.read_text(encoding="utf-8", errors="replace")
        yield Document(id=str(path.relative_to(root)), text=text, source=source)


def _require_snapshot(root: Path) -> None:
    if not root.exists() or not any(root.iterdir()):
        raise FileNotFoundError(
            f"Snapshot missing or empty at {root}. "
            "Fetch the corpus first (run `make index`, which fetches the pinned refs)."
        )
