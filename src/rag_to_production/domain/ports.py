from typing import Protocol

from rag_to_production.domain.models import Chunk, RetrievedChunk


class EmbedderPort(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...


class VectorStorePort(Protocol):
    def reset(self) -> None: ...

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None: ...

    def search(self, query_embedding: list[float], k: int) -> list[RetrievedChunk]: ...


class LLMPort(Protocol):
    def generate(self, prompt: str) -> str: ...
