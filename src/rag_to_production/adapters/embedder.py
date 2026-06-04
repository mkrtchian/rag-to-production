from typing import Any, cast

from sentence_transformers import SentenceTransformer


class SentenceTransformersEmbedder:
    def __init__(self, model_name: str) -> None:
        self._model = SentenceTransformer(model_name, device="cpu")

    def embed(self, texts: list[str]) -> list[list[float]]:
        embeddings = self._model.encode(  # pyright: ignore[reportUnknownMemberType]
            texts,
            batch_size=32,
            normalize_embeddings=True,
            convert_to_numpy=True,
            show_progress_bar=False,
        )
        return cast(list[list[float]], cast(Any, embeddings).tolist())
