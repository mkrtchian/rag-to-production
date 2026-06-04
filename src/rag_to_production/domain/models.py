from dataclasses import dataclass


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    source: str  # "docs" | "api_ref" | "issues"
    # naive baseline keeps source for display only; it is NOT used to filter
    # retrieval (that absence is a named limit -> Pattern 8 metadata, step 5)


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    document_id: str
    source: str


@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float  # higher = more relevant (cosine similarity), never a raw distance


@dataclass(frozen=True)
class RagAnswer:
    text: str
    # the retrieved chunks, NOT model-produced citations (real citation validation is step 5)
    retrieved_context: list[RetrievedChunk]


@dataclass(frozen=True)
class IndexStats:
    documents_per_source: dict[str, int]
    chunks_per_source: dict[str, int]
