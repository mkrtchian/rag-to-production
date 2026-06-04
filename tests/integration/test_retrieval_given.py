from pathlib import Path

from rag_to_production.adapters.embedder import SentenceTransformersEmbedder
from rag_to_production.adapters.vector_store import ChromaVectorStore
from rag_to_production.domain.chunking import ChunkingPolicy
from rag_to_production.domain.models import Document

_EMBEDDER_MODEL = "BAAI/bge-small-en-v1.5"


def a_corpus_with_a_distinctive_chunk() -> list[Document]:
    return [
        Document(
            id="doc-edges",
            text="Use add_conditional_edges to route a graph to different nodes based on state.",
            source="docs",
        ),
        Document(
            id="doc-checkpoint",
            text="A checkpointer persists graph state so a thread resumes after an interruption.",
            source="docs",
        ),
        Document(
            id="doc-streaming",
            text="Streaming emits tokens incrementally while the model produces an answer.",
            source="docs",
        ),
    ]


def a_real_embedder() -> SentenceTransformersEmbedder:
    return SentenceTransformersEmbedder(_EMBEDDER_MODEL)


def a_temp_dir_store(tmp_path: Path) -> ChromaVectorStore:
    return ChromaVectorStore(tmp_path / "chroma")


def the_naive_chunking_policy() -> ChunkingPolicy:
    return ChunkingPolicy(chunk_size=1000, overlap=200)
