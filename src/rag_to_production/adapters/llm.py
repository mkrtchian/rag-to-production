from google import genai


class GeminiLLM:
    def __init__(self, model: str, api_key: str) -> None:
        if not api_key:
            raise ValueError(
                "GEMINI_API_KEY is required to generate answers. "
                "Set it in the environment before running a query (indexing does not need it)."
            )
        self._model = model
        self._client = genai.Client(api_key=api_key)

    def generate(self, prompt: str) -> str:
        response = self._client.models.generate_content(  # pyright: ignore[reportUnknownMemberType]
            model=self._model, contents=prompt
        )
        return response.text or ""
