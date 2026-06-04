.PHONY: index fetch-issues test lint type format

index:
	uv run rag index

# Re-curate the committed LangGraph issue snapshot (needs `gh` authenticated).
# The jsonl is committed and frozen; this regenerates it at a new extraction date.
fetch-issues:
	uv run python scripts/fetch_langgraph_issues.py

test:
	uv run pytest

lint:
	uv run ruff check .

type:
	uv run pyright

format:
	uv run ruff format .
