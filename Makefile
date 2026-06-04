.PHONY: index fetch-issues test test-unit test-integration lint type format

index:
	uv run rag index

# Re-curate the committed LangGraph issue snapshot (needs `gh` authenticated).
# The jsonl is committed and frozen; this regenerates it at a new extraction date.
fetch-issues:
	uv run python scripts/fetch_langgraph_issues.py

# Fast, in-process tests. No model load, run on every save.
test-unit:
	uv run pytest tests/unit

# Real out-of-process components (embedder, vector store). Slower.
test-integration:
	uv run pytest tests/integration

test:
	uv run pytest

lint:
	uv run ruff check .

type:
	uv run pyright

format:
	uv run ruff format .
