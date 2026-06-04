from collections.abc import Iterator
from pathlib import Path

from rag_to_production.domain.models import Document

_DOC_SUFFIXES = (".mdx", ".md")


def load_docs(snapshot_dir: Path, prose_path: str) -> Iterator[Document]:
    root = snapshot_dir / "docs" / prose_path
    _require_snapshot(root)
    for path in sorted(root.rglob("*")):
        if path.suffix.lower() not in _DOC_SUFFIXES or not path.is_file():
            continue
        # mdx is treated as plain text: frontmatter and code fences are not parsed
        # out (naive baseline, a named chunking limit).
        text = path.read_text(encoding="utf-8", errors="replace")
        yield Document(id=str(path.relative_to(root)), text=text, source="docs")


def _require_snapshot(root: Path) -> None:
    if not root.exists() or not any(root.iterdir()):
        raise FileNotFoundError(
            f"Snapshot missing or empty at {root}. "
            "Fetch the corpus first (run `make index`, which fetches the pinned ref)."
        )
