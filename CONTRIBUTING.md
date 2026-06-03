# Contributing

Thanks for considering a contribution.

## Setup

```bash
git clone https://github.com/mkrtchian/rag-to-production.git
cd rag-to-production
uv sync
uv run pytest
```

You need Python 3.13+. The project uses [uv](https://docs.astral.sh/uv/) for dependency management. Do not add a `requirements.txt`.

```bash
uv run pytest            # tests
uv run ruff check .      # lint
uv run ruff format .     # format
uv run pyright           # type check
```

## Standards

Coding, testing, and architecture standards are defined in [CLAUDE.md](CLAUDE.md), the single source of truth for both human contributors and AI-assisted development. The short version: small pure functions, ports for I/O, fakes over mocks, behavior-based tests.

## AI-assisted development

For non-trivial changes, write a plan in `plans/` before implementation, using the [spec-driven-dev](https://github.com/mkrtchian/spec-driven-dev) workflow. Naming: `YYYY-MM-DD_short_description.md`. The plan is reviewed and approved before any code is written.

## Architecture decisions

Recorded in `docs/adr/` as immutable ADRs. To change a past decision, write a new ADR that supersedes it.

## License

By contributing, you agree that your contributions are licensed under the [MIT License](LICENSE).
