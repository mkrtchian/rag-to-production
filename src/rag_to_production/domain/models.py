from dataclasses import dataclass
from typing import Literal

# The corpus layers (ADR 003).
Source = Literal["docs", "api_ref", "issues"]


@dataclass(frozen=True)
class Document:
    id: str
    text: str
    source: Source
    # naive baseline keeps source for display only; it is NOT used to filter
    # retrieval (that absence is a named limit -> Pattern 8 metadata, step 5)


@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    document_id: str
    source: Source


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


@dataclass(frozen=True)
class ProseSource:
    """Pinned origin of the prose layer: the subtree `path` of `repo` at `ref`."""

    repo: str
    ref: str
    path: str


@dataclass(frozen=True)
class SourceCheckout:
    """Pinned origin of the API-reference layer: the package subtrees `paths` of `repo` at `ref`.

    Each path is a `langgraph` package directory (its basename is the top-level
    package, its parent is the prefix stripped to derive module qualnames).
    """

    repo: str
    ref: str
    paths: tuple[str, ...]
