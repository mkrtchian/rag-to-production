from dataclasses import dataclass

from rag_to_production.domain.models import Chunk, Document


@dataclass(frozen=True)
class ChunkingPolicy:
    chunk_size: int
    overlap: int

    def __post_init__(self) -> None:
        if self.chunk_size <= 0:
            raise ValueError(f"chunk_size must be positive, got {self.chunk_size}")
        if not 0 <= self.overlap < self.chunk_size:
            raise ValueError(f"overlap must be in [0, {self.chunk_size}), got {self.overlap}")


def chunk_document(doc: Document, policy: ChunkingPolicy) -> list[Chunk]:
    stride = policy.chunk_size - policy.overlap
    starts = range(0, max(len(doc.text), 1), stride)
    return [_chunk_at(doc, start, index, policy) for index, start in enumerate(starts)]


def _chunk_at(doc: Document, start: int, index: int, policy: ChunkingPolicy) -> Chunk:
    return Chunk(
        id=f"{doc.id}#{index}",
        text=doc.text[start : start + policy.chunk_size],
        document_id=doc.id,
        source=doc.source,
    )
