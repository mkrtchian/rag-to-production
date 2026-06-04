import tests.unit.fakes as fakes
from rag_to_production.domain.chunking import ChunkingPolicy
from rag_to_production.domain.models import Chunk, Document, RetrievedChunk, Source
from rag_to_production.domain.prompts import build_rag_prompt
from rag_to_production.pipeline import answer_query, index_corpus


def _document(doc_id: str, length: int, source: Source) -> Document:
    return Document(id=doc_id, text="x" * length, source=source)


def _retrieved(text: str, score: float) -> RetrievedChunk:
    chunk = Chunk(id=text, text=text, document_id="d", source="docs")
    return RetrievedChunk(chunk=chunk, score=score)


def test_index_corpus_counts_documents_and_chunks_per_source():
    documents = [
        _document("d1", length=250, source="docs"),
        _document("d2", length=100, source="docs"),
        _document("i1", length=250, source="issues"),
    ]
    policy = ChunkingPolicy(chunk_size=100, overlap=20)
    embedder = fakes.FakeEmbedder()
    store = fakes.FakeVectorStore()

    stats = index_corpus(documents, embedder, store, policy)

    # stride 80: d1 (len 250) -> 4 chunks, d2 (len 100) -> 2 chunks, i1 -> 4 chunks
    assert stats.documents_per_source == {"docs": 2, "issues": 1}
    assert stats.chunks_per_source == {"docs": 6, "issues": 4}


def test_index_corpus_adds_embedded_chunks_to_the_store():
    documents = [_document("d1", length=100, source="docs")]
    policy = ChunkingPolicy(chunk_size=100, overlap=20)
    embedder = fakes.FakeEmbedder()
    store = fakes.FakeVectorStore()

    index_corpus(documents, embedder, store, policy)

    assert [chunk.document_id for chunk in store.added_chunks] == ["d1", "d1"]
    assert len(store.added_embeddings) == len(store.added_chunks)


def test_answer_query_returns_topk_context_and_llm_text():
    nearest = [_retrieved("about conditional edges", 0.9), _retrieved("about state", 0.8)]
    store = fakes.FakeVectorStore(nearest=nearest)
    embedder = fakes.FakeEmbedder()
    llm = fakes.FakeLLM(answer="grounded answer")

    answer = answer_query("how to add a conditional edge", embedder, store, llm, k=2)

    assert answer.retrieved_context == nearest
    assert answer.text == "grounded answer"
    assert llm.received_prompt == build_rag_prompt("how to add a conditional edge", nearest)


def test_answer_query_still_answers_when_no_relevant_chunk_exists():
    store = fakes.FakeVectorStore(nearest=[])
    embedder = fakes.FakeEmbedder()
    llm = fakes.FakeLLM(answer="invented answer")

    answer = answer_query("a query with no support", embedder, store, llm, k=5)

    assert answer.retrieved_context == []
    assert answer.text == "invented answer"
