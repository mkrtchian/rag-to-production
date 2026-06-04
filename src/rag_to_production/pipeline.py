from collections import Counter
from collections.abc import Iterable

from rag_to_production.domain.chunking import ChunkingPolicy, chunk_document
from rag_to_production.domain.models import Chunk, Document, IndexStats, RagAnswer
from rag_to_production.domain.ports import EmbedderPort, LLMPort, VectorStorePort
from rag_to_production.domain.prompts import build_rag_prompt


def index_corpus(
    documents: Iterable[Document],
    embedder: EmbedderPort,
    store: VectorStorePort,
    policy: ChunkingPolicy,
) -> IndexStats:
    documents_per_source: Counter[str] = Counter()
    chunks_per_source: Counter[str] = Counter()
    for document in documents:
        chunks = chunk_document(document, policy)
        _add_chunks(chunks, embedder, store)
        documents_per_source[document.source] += 1
        chunks_per_source[document.source] += len(chunks)
    return IndexStats(
        documents_per_source=dict(documents_per_source),
        chunks_per_source=dict(chunks_per_source),
    )


def answer_query(
    query: str,
    embedder: EmbedderPort,
    store: VectorStorePort,
    llm: LLMPort,
    k: int,
) -> RagAnswer:
    query_embedding = embedder.embed([query])[0]
    retrieved = store.search(query_embedding, k)
    prompt = build_rag_prompt(query, retrieved)
    return RagAnswer(text=llm.generate(prompt), retrieved_context=retrieved)


def _add_chunks(chunks: list[Chunk], embedder: EmbedderPort, store: VectorStorePort) -> None:
    if not chunks:
        return
    embeddings = embedder.embed([chunk.text for chunk in chunks])
    store.add(chunks, embeddings)
