from itertools import pairwise

from rag_to_production.domain.models import Chunk


def chunk_count_is(chunks: list[Chunk], expected: int) -> None:
    assert len(chunks) == expected


def adjacent_chunks_overlap_by(chunks: list[Chunk], overlap: int) -> None:
    for previous, following in pairwise(chunks):
        shared = min(overlap, len(following.text))
        assert previous.text[-shared:] == following.text[:shared]


def every_chunk_carries(chunks: list[Chunk], *, document_id: str, source: str) -> None:
    assert chunks
    for chunk in chunks:
        assert chunk.document_id == document_id
        assert chunk.source == source


def chunk_ids_are_unique_and_derived_from(chunks: list[Chunk], document_id: str) -> None:
    ids = [chunk.id for chunk in chunks]
    assert len(ids) == len(set(ids))
    for chunk in chunks:
        assert chunk.id.startswith(document_id)


def the_code_fence_is_split_across_chunks(chunks: list[Chunk]) -> None:
    fenced = [chunk for chunk in chunks if "```" in chunk.text]
    assert fenced, "expected at least one chunk to contain a fence marker"
    # naive char-window chunking cuts the fence: no single chunk holds the
    # complete opening+closing pair, so the block is broken across chunks.
    assert all(chunk.text.count("```") < 2 for chunk in fenced)
