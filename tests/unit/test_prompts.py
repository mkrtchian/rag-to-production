from rag_to_production.domain.models import Chunk, RetrievedChunk
from rag_to_production.domain.prompts import build_rag_prompt


def _retrieved(text: str, score: float) -> RetrievedChunk:
    chunk = Chunk(id="c", text=text, document_id="d", source="docs")
    return RetrievedChunk(chunk=chunk, score=score)


def test_prompt_contains_query_and_every_chunk_text():
    query = "how do I add a conditional edge"
    chunks = [_retrieved("first context", 0.9), _retrieved("second context", 0.8)]

    prompt = build_rag_prompt(query, chunks)

    assert query in prompt
    assert "first context" in prompt
    assert "second context" in prompt


def test_chunks_appear_in_retrieval_order():
    chunks = [_retrieved("alpha", 0.9), _retrieved("beta", 0.8)]

    prompt = build_rag_prompt("q", chunks)

    assert prompt.index("alpha") < prompt.index("beta")


def test_zero_chunks_still_produces_a_non_empty_prompt():
    prompt = build_rag_prompt("a query with no context", [])

    assert prompt.strip()
    assert "a query with no context" in prompt
