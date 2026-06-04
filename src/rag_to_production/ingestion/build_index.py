from collections.abc import Iterator
from itertools import chain

from rag_to_production.adapters.embedder import SentenceTransformersEmbedder
from rag_to_production.adapters.vector_store import ChromaVectorStore
from rag_to_production.config import Settings
from rag_to_production.domain.models import Document, IndexStats
from rag_to_production.ingestion.corpus import load_api_reference, load_docs
from rag_to_production.ingestion.issues import load_issues
from rag_to_production.ingestion.snapshot import fetch_snapshot
from rag_to_production.pipeline import index_corpus


def main() -> None:
    settings = Settings()
    fetch_snapshot(settings.snapshot_dir, settings.docs_ref, settings.langgraph_ref)
    embedder = SentenceTransformersEmbedder(settings.embedder_model)
    store = ChromaVectorStore(settings.chroma_dir)
    stats = index_corpus(_load_corpus(settings), embedder, store, settings.chunking)
    _print_stats(stats)


def _load_corpus(settings: Settings) -> Iterator[Document]:
    return chain(
        load_docs(settings.snapshot_dir),
        load_api_reference(settings.snapshot_dir),
        load_issues(settings.issues_path),
    )


def _print_stats(stats: IndexStats) -> None:
    print("Index built. Documents and chunks per source:")
    for source in sorted(stats.documents_per_source):
        documents = stats.documents_per_source[source]
        chunks = stats.chunks_per_source.get(source, 0)
        print(f"  {source}: {documents} documents, {chunks} chunks")


if __name__ == "__main__":
    main()
