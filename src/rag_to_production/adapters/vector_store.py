from pathlib import Path
from typing import cast

import chromadb
from chromadb import Collection, Metadata
from chromadb.api.types import PyEmbeddings

from rag_to_production.domain.models import Chunk, RetrievedChunk, Source

_COLLECTION_NAME = "corpus"


class ChromaVectorStore:
    def __init__(self, persist_dir: Path) -> None:
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._create_collection()

    def reset(self) -> None:
        # Drop and recreate the one corpus collection so a build starts clean. This
        # is per-collection, not chromadb's global client.reset() (which wipes the
        # whole database and is settings-gated).
        self._client.delete_collection(_COLLECTION_NAME)
        self._collection = self._create_collection()

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        as_embeddings: PyEmbeddings = list(embeddings)
        metadatas: list[Metadata] = [
            {"document_id": chunk.document_id, "source": chunk.source} for chunk in chunks
        ]
        self._collection.add(
            ids=[chunk.id for chunk in chunks],
            embeddings=as_embeddings,
            documents=[chunk.text for chunk in chunks],
            metadatas=metadatas,
        )

    def search(self, query_embedding: list[float], k: int) -> list[RetrievedChunk]:
        hits = self._collection.query(query_embeddings=[query_embedding], n_results=k)
        return [
            _to_retrieved_chunk(chunk_id, text, metadata, distance)
            for chunk_id, text, metadata, distance in zip(
                hits["ids"][0],
                _column(hits["documents"]),
                _column(hits["metadatas"]),
                _column(hits["distances"]),
                strict=True,
            )
        ]

    def _create_collection(self) -> Collection:
        return self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            configuration={"hnsw": {"space": "cosine"}},
        )


def _to_retrieved_chunk(
    chunk_id: str,
    text: str,
    metadata: Metadata,
    distance: float,
) -> RetrievedChunk:
    chunk = Chunk(
        id=chunk_id,
        text=text,
        document_id=str(metadata["document_id"]),
        # the store round-trips a known corpus layer; cast at this untyped boundary
        source=cast("Source", str(metadata["source"])),
    )
    # Chroma returns a cosine distance (lower = closer); convert once to a
    # similarity score so callers always sort by score descending.
    return RetrievedChunk(chunk=chunk, score=1.0 - distance)


def _column[T](rows: list[list[T]] | None) -> list[T]:
    return rows[0] if rows else []
