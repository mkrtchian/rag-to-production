from rag_to_production.domain.chunking import ChunkingPolicy
from rag_to_production.domain.models import Document, Source


def a_document_of_length(length: int, *, source: Source = "docs") -> Document:
    text = "".join(chr(ord("a") + (i % 26)) for i in range(length))
    return Document(id="doc-1", text=text, source=source)


def a_document_with_a_code_fence() -> Document:
    text = "intro text " + "```python\nprint('hello')\n``` " + "x" * 40
    return Document(id="doc-fence", text=text, source="docs")


def a_policy(*, chunk_size: int, overlap: int) -> ChunkingPolicy:
    return ChunkingPolicy(chunk_size=chunk_size, overlap=overlap)
