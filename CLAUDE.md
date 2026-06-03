# rag-to-production

Guidance for working in this repository. Single source of truth for human and AI-assisted contributions.

## Commands

```bash
uv sync                       # install dev dependencies
uv run pytest                 # tests
uv run ruff check .           # lint
uv run ruff format .          # format
uv run pyright                # type check (strict)
```

Eval commands are added as the evaluation harness lands (see the roadmap in README.md and the relevant plan in `plans/`).

## Coding standards

- Code in the tradition of **Kent Beck**, **Martin Fowler**, **Robert C. Martin**, **Eric Evans**: XP, software craftsmanship, DDD.
- **Prefer pure functions.** Same inputs, same output, no side effects. Maximise the transformational core (parsing, chunking, prompt construction, metrics, ranking, rendering). When a function needs I/O, inject the dependency through a Port (a `Protocol`). Never hide I/O, env, or clock access behind a direct call.
- **Prompts are domain logic, not infrastructure.** They live as pure functions `(data) -> str`, never built inside adapters.
- All code, comments, docstrings, and identifiers in **English**.
- **Newspaper rule** (Clean Code): read a module top to bottom like an article. Public, high-level functions first, private helpers right below their callers.
- Functions rarely exceed **20 lines**, files rarely exceed **300 lines**. When they do, split.
- **Few arguments** (aim for 3 or fewer). When parameters accumulate, a concept is missing: extract a value object, dataclass, or Protocol that names the grouping. The fix is not a generic `params` dict but a domain-relevant name.
- **Naming over comments.** Code should read without them. Reserve comments for non-obvious logic, hacks, or workarounds. Same rule for docstrings: do not restate the class or function name in prose. Use **domain-relevant, readable names**, no abbreviations except in very short scopes (e.g. comprehensions).

The concrete module boundary (the hexagonal layout) is decided at the architecture step and recorded in an ADR, not fixed up front. The principles above hold regardless of the layout.

## Testing standards

- Test **behavior**, not implementation. Assert on observable outcomes, never on internal call sequences.
- **Fakes, not mocks.** Fakes are real implementations with deterministic, configurable behavior. Mocks couple tests to how code calls its dependencies.
- **Three levels.** Unit and integration both assert exact outcomes. They split on the process boundary. Evals are a different kind: they score quality against a ground truth.
  - **unit** (in-process, fakes): pure logic, routing, prompt construction, metric computation, rendering. No out-of-process dependency. Asserts exact outcomes.
  - **integration** (real out-of-process components, no LLM): the wiring is correct. The retrieval adapter talks to a real store, a known query returns the expected chunk. Deterministic, asserts exact outcomes.
  - **evals** (`evals/`, against a ground truth): quality measured as a score with a threshold, not a fixed assertion. That score-versus-assertion difference is what separates an eval from a test. Two kinds: a **retrieval eval** (LLM-free, deterministic, IR metrics like recall@k and precision@k, the contract layer) and a **generation eval** (LLM-as-a-judge, non-deterministic, faithfulness and relevance, the quality layer). **Never measure quality with fakes**, that is what evals are for.
- **Given/When/Then pattern**: test files stay ultra-readable by extracting setup into `given.py` and assertions into `then.py`, one pair per test file (e.g. `test_retrieval.py` + `test_retrieval_given.py` + `test_retrieval_then.py`). The test file reads like a spec. Only extract into given/then when the function **actually abstracts something**. If it is just a one-liner wrapper, inline it instead.

```python
# test_retrieval.py
import tests.unit.test_retrieval_given as given
import tests.unit.test_retrieval_then as then

def test_hybrid_retrieval_beats_baseline_on_acronym_queries():
    corpus = given.a_corpus_with_acronym_chunks()
    retriever = given.a_hybrid_retriever(corpus)
    query = "what is the TTL field"  # trivial, inline

    results = retriever.search(query, k=5)

    then.results_contain_chunk_about(results, term="TTL")
```

## Workflow

- **Test-first** for business logic: write the test, watch it fail, then implement. Glue and config do not need a test-first dance.
- Run unit tests after each meaningful change, not only at the end.
- Refactor on green before moving on.

## Pointers

- `docs/adr/`: Architecture Decision Records. Explain **why**, not how. **Immutable once accepted**: to change a decision, write a new ADR that supersedes it.
- `plans/`: spec-driven development. Before a non-trivial feature, write a plan as `YYYY-MM-DD_short_description.md`, get it reviewed, then implement. **Immutable once implemented**: plans are a historical record, not living docs.
- `README.md`: the program and roadmap.
