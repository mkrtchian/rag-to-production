from rag_to_production.domain.models import RetrievedChunk

_INSTRUCTION = "Answer the question using the context below."


def build_rag_prompt(query: str, chunks: list[RetrievedChunk]) -> str:
    context = "\n\n".join(_render_chunk(index, retrieved) for index, retrieved in enumerate(chunks))
    return f"{_INSTRUCTION}\n\nContext:\n{context}\n\nQuestion: {query}\n\nAnswer:"


def _render_chunk(index: int, retrieved: RetrievedChunk) -> str:
    return f"[{index + 1}] {retrieved.chunk.text}"
