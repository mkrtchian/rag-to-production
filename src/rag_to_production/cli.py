import argparse
import os
import sys
from collections.abc import Iterator
from itertools import chain

from rag_to_production.adapters.embedder import SentenceTransformersEmbedder
from rag_to_production.adapters.llm import GeminiLLM
from rag_to_production.adapters.vector_store import ChromaVectorStore
from rag_to_production.config import Settings
from rag_to_production.domain.models import Document, IndexStats, RagAnswer
from rag_to_production.ingestion.api_reference import load_api_reference
from rag_to_production.ingestion.corpus import load_docs
from rag_to_production.ingestion.issues import load_issues
from rag_to_production.ingestion.snapshot import fetch_snapshot, fetch_source_snapshot
from rag_to_production.pipeline import answer_query, index_corpus


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    settings = Settings()
    if args.command == "index":
        return run_index(settings)
    return run_query(settings, args.question, os.environ.get("GEMINI_API_KEY", ""))


def run_index(settings: Settings) -> int:
    fetch_snapshot(settings.snapshot_dir, settings.docs)
    fetch_source_snapshot(settings.snapshot_dir, settings.api_ref)
    embedder = SentenceTransformersEmbedder(settings.embedder_model)
    store = ChromaVectorStore(settings.chroma_dir)
    stats = index_corpus(_load_corpus(settings), embedder, store, settings.chunking)
    print(_render_stats(stats))
    return 0


def run_query(settings: Settings, question: str, api_key: str) -> int:
    try:
        llm = GeminiLLM(settings.llm_model, api_key)
    except ValueError as error:
        print(error, file=sys.stderr)
        return 1
    embedder = SentenceTransformersEmbedder(settings.embedder_model)
    store = ChromaVectorStore(settings.chroma_dir)
    answer = answer_query(question, embedder, store, llm, settings.k)
    print(_render_answer(answer))
    return 0


def _parse_args(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="rag", description="Baseline RAG over the LangGraph corpus."
    )
    subcommands = parser.add_subparsers(dest="command", required=True)
    subcommands.add_parser("index", help="Build the vector index from the pinned corpus snapshot.")
    query = subcommands.add_parser("query", help="Answer a question against the built index.")
    query.add_argument("question", help="The question to answer.")
    return parser.parse_args(argv)


def _load_corpus(settings: Settings) -> Iterator[Document]:
    return chain(
        load_docs(settings.snapshot_dir, settings.docs.path),
        load_api_reference(settings.snapshot_dir, settings.api_ref),
        load_issues(settings.issues_path),
    )


def _render_stats(stats: IndexStats) -> str:
    lines = ["Index built. Documents and chunks per source:"]
    for source in sorted(stats.documents_per_source):
        documents = stats.documents_per_source[source]
        chunks = stats.chunks_per_source.get(source, 0)
        lines.append(f"  {source}: {documents} documents, {chunks} chunks")
    return "\n".join(lines)


def _render_answer(answer: RagAnswer) -> str:
    sources = ", ".join(
        f"{retrieved.chunk.source}:{retrieved.chunk.document_id}"
        for retrieved in answer.retrieved_context
    )
    return f"{answer.text}\n\nRetrieved context: {sources}"


if __name__ == "__main__":
    sys.exit(main())
