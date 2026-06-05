# Plan: load secrets from a gitignored `.env`

## Context

`GEMINI_API_KEY` is currently read from the shell environment at the composition
root (`cli.py:main`, line 24: `os.environ.get("GEMINI_API_KEY", "")`). The query
path needs it; indexing does not. Having to `export GEMINI_API_KEY=...` in every
new shell is tedious and easy to forget.

The fix is the standard one: a gitignored `.env` holding local secrets, plus a
committed `.env.example` template a contributor copies and fills. A loader reads
`.env` into the process environment at startup.

This must respect [ADR 004](../docs/adr/004-baseline-architecture.md): environment
access happens **explicitly at the composition root** and is never hidden behind a
config object. `pydantic-settings` was rejected there for exactly that reason. So
the loader is an explicit `load_dotenv()` call at the top of `main()`, and the
existing `os.environ.get("GEMINI_API_KEY", "")` line stays as-is. `Settings`
remains a values-only frozen dataclass with no env access.

## Approach

Add `python-dotenv`, call `load_dotenv()` as the first statement in `main()`.
With the default `override=False`, a value already set in the shell wins over the
`.env` file, so `.env` is a fallback for unset keys, not an override. If `.env` is
absent, `load_dotenv()` is a no-op and behavior is identical to today (read from
the shell). The downstream `os.environ.get` call is untouched.

This is composition-root glue around a third-party library, not business logic, so
no test-first dance and no new unit test (per CLAUDE.md: "Glue and config do not
need a test-first dance"). Asserting `load_dotenv()` populates `os.environ` would
just test the library.

## Files to modify

### `pyproject.toml`
Add `python-dotenv` to `dependencies` (line 18):

```toml
dependencies = ["chromadb", "sentence-transformers", "google-genai", "httpx", "python-dotenv"]
```

Run `uv add python-dotenv` (updates `pyproject.toml` and `uv.lock` together)
rather than hand-editing, so the lock stays consistent.

### `src/rag_to_production/cli.py`
Import at the top of the import block:

```python
from dotenv import load_dotenv
```

Call it as the first line of `main()`:

```python
def main(argv: list[str] | None = None) -> int:
    load_dotenv()
    args = _parse_args(argv)
    settings = Settings()
    if args.command == "index":
        return run_index(settings)
    return run_query(settings, args.question, os.environ.get("GEMINI_API_KEY", ""))
```

Nothing else in `cli.py` changes. `os` stays imported (still used on line 24).

### `.env.example` (new, committed)
A template with the key present but empty and a one-line comment pointing at the
README. Keep it to what the project actually reads today (only `GEMINI_API_KEY`):

```
# Copy to .env and fill in. Required for `rag query`, not for `rag index`.
# See README "Getting started". The shell environment, if set, takes precedence.
GEMINI_API_KEY=
```

### `README.md`
Update the "Getting started" code block (lines 43-48) to use the `.env` flow instead
of a bare `export`:

```bash
uv sync                                              # install dependencies
cp .env.example .env                                 # then put your key in .env (query only, not index)
make index                                           # fetch the corpus and build the index
uv run rag query "how do I add a conditional edge in LangGraph?"
```

Adjust the prose under the block: the query path reads `GEMINI_API_KEY` from `.env`
(loaded at startup) or the shell environment, the shell taking precedence. Keep the
existing point that indexing needs no key.

## What stays unchanged

- `os.environ.get("GEMINI_API_KEY", "")` on the (renumbered) query line: the read
  stays explicit at the composition root.
- `Settings` (`config.py`): still values-only, no env access, no `.env` knowledge.
- `GeminiLLM` (`adapters/llm.py`): still receives the key as a constructor argument
  and still raises the clear `ValueError` when it is empty.
- `.gitignore`: already lists `.env` (under "# Environment"). `.env.example` is a
  different filename, not matched by that pattern, so it commits without change.
- The `make index` / `make fetch-issues` targets and all tests.

## Edge cases

- **No `.env` file**: `load_dotenv()` is a silent no-op; the key resolves from the
  shell exactly as today. Indexing keeps working with no key anywhere.
- **Key in both shell and `.env`**: `override=False` (the default) means the shell
  value wins. Documented in `.env.example` and the README.
- **`.env` present but `GEMINI_API_KEY` empty/absent**: `os.environ.get` returns
  `""`, `GeminiLLM.__init__` raises its existing `ValueError`, `run_query` prints it
  to stderr and returns 1. Unchanged failure path.
- **`rag index` with a `.env` present**: `load_dotenv()` runs but the key is never
  read on the index path. Harmless.

## Verification

```bash
uv add python-dotenv          # adds dep + updates uv.lock
uv sync
uv run ruff check .
uv run ruff format .
uv run pyright                # strict; load_dotenv is typed
make test-unit                # nothing should regress

# Manual end-to-end of the new flow (needs a real key + built index):
cp .env.example .env          # then edit .env to set GEMINI_API_KEY=...
unset GEMINI_API_KEY          # prove the shell export is no longer required
uv run rag query "how do I add a conditional edge in LangGraph?"

# Prove the absent-.env fallback still works:
rm .env
export GEMINI_API_KEY=...     # back to the shell path
uv run rag query "..."        # still answers

# Confirm the template is tracked and the secret is not:
git status --short            # .env.example staged, .env absent from the list
git check-ignore .env         # prints ".env" (ignored)
```

## Implementation steps

### Step 1: load `.env` at the composition root

**Files**:
- `pyproject.toml` (modify, via `uv add`) + `uv.lock` (regenerated)
- `src/rag_to_production/cli.py` (modify)
- `.env.example` (new, committed)
- `README.md` (modify, "Getting started" section)

**Do** (config and glue, no test-first dance per CLAUDE.md):

1. Add the dependency with `uv add python-dotenv` (do not hand-edit). This updates the `dependencies` list in `pyproject.toml` and `uv.lock` together. Confirm `dependencies` now reads `["chromadb", "sentence-transformers", "google-genai", "httpx", "python-dotenv"]`.

2. In `src/rag_to_production/cli.py`: add `from dotenv import load_dotenv` to the third-party import block (after the stdlib imports on lines 1-5, before the `rag_to_production` imports). Add `load_dotenv()` as the first statement inside `main()` (currently line 20, above `args = _parse_args(argv)`). Leave everything else untouched: `os` stays imported (used line 24), and `os.environ.get("GEMINI_API_KEY", "")` on the (renumbered) query line stays exactly as-is. `load_dotenv()` defaults to `override=False`, so a shell value wins over `.env`.

3. Create `.env.example` (committed) with exactly:
   ```
   # Copy to .env and fill in. Required for `rag query`, not for `rag index`.
   # See README "Getting started". The shell environment, if set, takes precedence.
   GEMINI_API_KEY=
   ```
   `.gitignore` matches `.env` but not `.env.example`, so the template commits normally.

4. In `README.md`, update the "Getting started" code block (lines 43-48): replace the `export GEMINI_API_KEY=...` line with `cp .env.example .env` and a comment that the key goes in `.env` (query only, not index). Adjust the prose under the block (line 50): the query path reads `GEMINI_API_KEY` from `.env` (loaded at startup) or the shell environment, the shell taking precedence. Keep the existing point that indexing needs no key.

**Test**: No new test. This is composition-root glue around a third-party library, not business logic (CLAUDE.md: "Glue and config do not need a test-first dance"). Asserting `load_dotenv()` populates `os.environ` would only test the library. The existing unit suite must not regress.

**Verify** (from the repo root):
```bash
uv add python-dotenv          # if not already run in step 1
uv sync
uv run ruff check .           # clean
uv run ruff format .          # no reformatting needed
uv run pyright                # strict, clean (load_dotenv is typed)
make test-unit                # nothing regresses
git check-ignore .env         # prints ".env" when a local .env exists (ignored)
```
Expect: lint/format/pyright clean, `make test-unit` green, `.env.example` tracked while `.env` stays ignored.
