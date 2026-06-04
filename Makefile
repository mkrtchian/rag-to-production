.PHONY: index test lint type format

index:
	uv run rag index

test:
	uv run pytest

lint:
	uv run ruff check .

type:
	uv run pyright

format:
	uv run ruff format .
