from rag_to_production.domain.models import Chunk, RetrievedChunk


class FakeEmbedder:
    def __init__(self) -> None:
        self.embedded_batches: list[list[str]] = []

    def embed(self, texts: list[str]) -> list[list[float]]:
        self.embedded_batches.append(texts)
        return [[float(len(text)), float(index)] for index, text in enumerate(texts)]


class FakeVectorStore:
    def __init__(self, nearest: list[RetrievedChunk] | None = None) -> None:
        self.added_chunks: list[Chunk] = []
        self.added_embeddings: list[list[float]] = []
        self._nearest = nearest or []

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None:
        self.added_chunks.extend(chunks)
        self.added_embeddings.extend(embeddings)

    def search(self, query_embedding: list[float], k: int) -> list[RetrievedChunk]:
        return self._nearest[:k]


class FakeLLM:
    def __init__(self, answer: str = "fake answer") -> None:
        self._answer = answer
        self.received_prompt: str | None = None

    def generate(self, prompt: str) -> str:
        self.received_prompt = prompt
        return self._answer
