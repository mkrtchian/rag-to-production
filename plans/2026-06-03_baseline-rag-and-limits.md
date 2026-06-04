# Baseline RAG and its named limits (Step 1)

**ADRs:** `docs/adr/003-corpus-langgraph.md`, `docs/adr/004-baseline-architecture.md`

## Context

Step 1 ships a deliberately naive RAG (index, retrieve, generate; single-vector
retrieval; fixed-size chunking; Lakshmanan & Hapke Pattern 6, "Basic RAG")
**plus** the table of why it breaks in production. It is the repository's
starting point and frames everything that follows.

Grounding. The construction follows the RAG pattern catalog of Lakshmanan &
Hapke, _Generative AI Design Patterns_ (chapters 3-4): seven patterns, Basic RAG
(P6) through Deep Search (P12), forming an escalator from demo to production,
each with explicit "when to use / when NOT to use" criteria. That catalog is why
this repository can say which pattern fixes which limit, and when a pattern is
not worth its cost. The failure modes and the retrieval-first,
measure-before-you-add discipline draw on practitioner sources: Skylar Payne's
RAG anti-patterns, the applied-llms consensus, Jason Liu's RAG evals, and the
Husain & Shankar evals FAQ. The limitation -> pattern table below is that
escalator made concrete on the LangGraph corpus.

Boundary to hold: step 1 **names and argues** the limits (from the literature
and on the real corpus), it does **not measure** them. Measurement is the
harness of step 2 (golden set, IR metrics, CI). "No measurement" is itself a
named limit in the table. The baseline runs end to end (generation included),
because the deliverable is a working baseline RAG, but only retrieval gets an
early eval (step 2); generation is evaluated at step 5.

Load-bearing nuance, easy to get backwards. The book's Pattern 6 baseline is
_keyword_ (TF-IDF/BM25); its "need for exact match" limit means keyword misses
_synonyms_ (ruptured vs broken), fixed by embeddings (Pattern 7). Our baseline
is _single-vector embeddings_, whose weakness is the opposite: it misses _exact
tokens_ (API names, symbols, error-class names, IDs), fixed by _hybrid_
retrieval (BM25 + vector, Pattern 9, Component 3, step 3). Grounded by
Lakshmanan p.171 ("a system that has only an embedding-based retriever ... will
be inadequate ... specific products, item-codes") and applied-llms ("embeddings
may struggle ... names (Ilya), acronyms (RAG), IDs (claude-3-sonnet)"). The
LangGraph corpus is saturated with this case (e.g. `add_conditional_edges`,
`InvalidUpdateError`), so the failure is real and reproducible, not fabricated.

Principle: naive, not strawman. Each naive choice is a default a real team would
ship, with its limit named, not a caricature broken on purpose. That is the
honest basis for the repository's "when NOT to add a pattern" thesis (Payne:
"in over 90% of these cases, the new system performed worse when properly
evaluated").

## Approach

A linear pipeline built from small, inspectable parts, hexagonal from the start
but minimal: a pure domain core (chunking, prompt construction), three ports
(`Embedder`, `VectorStore`, `LLM`) for the I/O the baseline actually uses, thin
adapters behind them, plain dependency injection (ports passed as arguments, no
framework, no `make_node` closures since there is no LangGraph here). The
architecture is not justified by an eval delta (a refactor produces none); its
payoff is shown later at the Chroma -> pgvector swap (step 3): same port, same
harness numbers, localized diff. Proof by invariance, not by delta.

Corpus: three layers (docs prose, API reference, a bounded curated set of issue
threads) from pinned refs, regenerable via `make index`, vector DB gitignored,
curated issues committed as data. Ingestion is naive on purpose: one shared
index, no metadata filtering. The pollution this causes (stale/contradictory
issue content) becomes a named limit, not something we fix now.

## Files to create

```
src/rag_to_production/
  domain/
    __init__.py
    models.py        # Document, Chunk, RetrievedChunk, RagAnswer, IndexStats
    ports.py         # EmbedderPort, VectorStorePort, LLMPort (Protocols)
    chunking.py      # pure: chunk_document(...)
    prompts.py       # pure: build_rag_prompt(...)
  adapters/
    __init__.py
    embedder.py      # SentenceTransformersEmbedder
    vector_store.py  # ChromaVectorStore
    llm.py           # GeminiLLM
  ingestion/
    __init__.py
    corpus.py        # load_corpus(...) -> Iterable[Document] from the snapshot
    snapshot.py      # fetch docs/api-ref at pinned refs (gitignored output)
    issues.py        # load committed curated issue threads
  pipeline.py        # index_corpus(...), answer_query(...)
  config.py          # Settings (model names, chunk params, k, paths, refs)
  cli.py             # `main()` dispatch -> `query` and `index` subcommands
                     #   (registered as the `rag` console script in pyproject)
data/
  langgraph-issues.jsonl   # committed curated issue threads
tests/
  unit/
    __init__.py
    test_chunking.py + test_chunking_given.py + test_chunking_then.py
    test_prompts.py         # no given/then: setup is one-liner, inlined
    fakes.py                # FakeEmbedder, FakeVectorStore, FakeLLM
  integration/
    __init__.py
    test_retrieval.py + test_retrieval_given.py + test_retrieval_then.py
docs/adr/003-corpus-langgraph.md
docs/adr/004-baseline-architecture.md
Makefile                    # `make index`, plus thin wrappers for test/lint/type
```

## Files to modify

- `README.md`: add two sections.
  (1) A **"Getting started"** section with the runnable quickstart: `uv sync`,
  `GEMINI_API_KEY` (queries only, not indexing), `make index`, then
  `uv run rag query "..."`. State that the vector store is embedded Chroma running
  in-process and persisting to a gitignored local dir (no service, no Docker at
  this stage; a managed store behind the same port and a `docker-compose` stack
  arrive at step 3, as the literal demo->production move), and that `make index`
  embeds on CPU and can be slow on the full corpus. The corpus is fetched from
  pinned refs, so the build is reproducible.
  (2) A **"Step 1: the baseline and why it breaks"** section containing the
  limitation -> pattern table below, opening with one sentence attributing the
  P6-P12 pattern catalog to Lakshmanan & Hapke, _Generative AI Design Patterns_
  (with a link), so the "Pattern 9" / "P11" references are legible to an outside
  reader.
  Do not touch the existing problem/method/roadmap/relationship/conventions
  sections.
- `pyproject.toml`: add runtime deps (`chromadb`, `sentence-transformers`,
  `google-genai`, `httpx` for snapshot fetch). Keep dev deps as is. Add a
  `[project.scripts]` entry `rag = "rag_to_production.cli:main"` so
  `uv run rag query ...` resolves (current `pyproject.toml` declares no script).
  Config is a plain frozen dataclass with env read at the composition root, so
  no `pydantic` / `pydantic-settings` (resolved at review).
- `.gitignore`: add the gitignored ingestion outputs (the Chroma persistent dir
  and the snapshot dir, e.g. `chroma/`, `snapshot/`, matching the `chroma_dir` /
  `snapshot_dir` config defaults). The current `.gitignore` covers only Python
  and env artifacts, so without this the vector DB and fetched docs would be
  committed. `data/langgraph-issues.jsonl` stays committed (not ignored).

## Files that stay unchanged

- `docs/adr/001-evaluation-strategy.md`, `docs/adr/002-no-orchestration-framework-v1.md`
  (immutable, accepted).
- `CLAUDE.md`, `CONTRIBUTING.md`, `LICENSE`, the README sections other than the
  new Getting started and step-1 sections.
- No eval, golden set, IR metric, CI workflow, BM25, reranker, cache,
  observability, or judge anywhere (later steps).

## Code details

### `domain/models.py`

```python
@dataclass(frozen=True)
class Document:
    id: str
    text: str
    source: str          # "docs" | "api_ref" | "issues"
    # naive baseline keeps source for display only; it is NOT used to filter
    # retrieval (that absence is a named limit -> Pattern 8 metadata, step 5)

@dataclass(frozen=True)
class Chunk:
    id: str
    text: str
    document_id: str
    source: str

@dataclass(frozen=True)
class RetrievedChunk:
    chunk: Chunk
    score: float        # higher = more relevant (cosine similarity), never a raw distance

@dataclass(frozen=True)
class RagAnswer:
    text: str
    retrieved_context: list[RetrievedChunk]  # the retrieved chunks, NOT model-produced citations (real citation validation is step 5)

@dataclass(frozen=True)
class IndexStats:
    documents_per_source: dict[str, int]
    chunks_per_source: dict[str, int]
```

`IndexStats` exists so `make index` prints document and chunk counts per source.
This is visibility only (so we can state corpus size honestly); it is not the
ingestion validation/alerting that Payne recommends, which stays a named gap.

### `domain/ports.py`

Generic ports, not domain-aware (mcp-auditor ADR 002 lesson: the port abstracts
_which model/store_, not _what question_). Synchronous: a linear batch-index +
single-query pipeline has no concurrency need (unlike mcp-auditor's async graph).

```python
class EmbedderPort(Protocol):
    def embed(self, texts: list[str]) -> list[list[float]]: ...

class VectorStorePort(Protocol):
    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None: ...
    def search(self, query_embedding: list[float], k: int) -> list[RetrievedChunk]: ...

class LLMPort(Protocol):
    def generate(self, prompt: str) -> str: ...
```

### `domain/chunking.py` (pure)

```python
@dataclass(frozen=True)
class ChunkingPolicy:
    chunk_size: int
    overlap: int

def chunk_document(doc: Document, policy: ChunkingPolicy) -> list[Chunk]: ...
```

Fixed-size character window with overlap, structure-blind: it does not respect
mdx frontmatter, headings, or code fences, so it cuts mid-unit. At the naive
default (1000 chars / 200 overlap) the named limit is this structure-blindness,
not Payne's "too small" tutorial default (~200 chars), which does not bite at
this size. `chunk_size`/`overlap` always travel together, so they are a
`ChunkingPolicy` value object (CLAUDE.md: "when parameters accumulate, a concept
is missing: extract a value object ... a domain-relevant name"), not two loose
scalars. The naive default `ChunkingPolicy` is named in config.

### `domain/prompts.py` (pure)

```python
def build_rag_prompt(query: str, chunks: list[RetrievedChunk]) -> str: ...
```

Stuffs the retrieved chunks and the query into a single instruction. Naive: no
citation-validation instruction, no abstention instruction, no version
disambiguation (each absence is a named limit -> Pattern 11, step 5).

### `pipeline.py` (plain DI)

```python
def index_corpus(
    documents: Iterable[Document],
    embedder: EmbedderPort,
    store: VectorStorePort,
    policy: ChunkingPolicy,
) -> IndexStats: ...

def answer_query(
    query: str,
    embedder: EmbedderPort,
    store: VectorStorePort,
    llm: LLMPort,
    k: int,
) -> RagAnswer: ...
```

Folding `chunk_size`/`overlap` into `ChunkingPolicy` keeps `index_corpus` at
four arguments (CLAUDE.md: "aim for 3 or fewer ... a generic `params` dict but a
domain-relevant name"). `answer_query` keeps `k` as a single scalar: it is the
only retrieval knob here, so there is no group to extract yet (CLAUDE.md warns
against premature abstraction). It joins a value object if more retrieval
parameters appear in a later step.

`answer_query` always returns the top-k and an answer, even when nothing
relevant exists (no abstention) -> named limit.

### `adapters/`

- `SentenceTransformersEmbedder`: wraps `sentence-transformers`, model from
  config (a CPU-viable small/base English retrieval model, exact model resolved
  at wiring). CPU.
- `ChromaVectorStore`: embedded Chroma (persistent dir, gitignored), cosine
  space. Implements `add`/`search`, and converts Chroma's distance into a `score`
  where higher = more relevant before mapping hits to `RetrievedChunk` (Chroma
  returns a distance, lower = closer; step-2 IR metrics sort by score descending,
  so the conversion happens here, once, not at the call sites).
- `GeminiLLM`: wraps `google-genai`, model from config (Gemini 3.1 Flash-Lite,
  exact `google-genai` model id resolved at wiring),
  `generate(prompt) -> str`. API key from env.

### `ingestion/`

- `snapshot.py`: fetch `langchain-ai/docs` and `langchain-ai/langgraph` at
  pinned ref SHAs (in config), into a gitignored local dir. Idempotent.
- `corpus.py`: walk the snapshot, yield `Document` for docs (mdx) and API-ref,
  treating mdx as plain text (naive: frontmatter and code fences are not parsed
  out).
- `issues.py`: read `data/langgraph-issues.jsonl` (curated, committed), yield
  `Document(source="issues")` per thread. The jsonl keeps the raw per-thread
  fields the GitHub fetch already returns (number, url, state, labels,
  created/closed dates, body + comments); step 1 projects only `text` and drops
  the rest. No step-1 code consumes the extra fields, they are kept as snapshot
  provenance so step 5 has the material (version, staleness, resolved-vs-open)
  without a non-reproducible re-fetch. Not premature: it is fetched data we
  decline to discard, not speculative code.

### `config.py`

`Settings` (frozen dataclass): `embedder_model`, `llm_model`,
`chunking` (a `ChunkingPolicy`), `k`, `chroma_dir`, `snapshot_dir`,
`docs_ref`, `langgraph_ref`, `issues_path`. Values are the single source of the
naive defaults named in the README. Env access (any override, plus
`GEMINI_API_KEY`) happens explicitly at the composition root (`cli.py`) and is
passed in, never read implicitly inside `Settings` (CLAUDE.md: no hidden env or
I/O access), which is why this is a plain dataclass and not `pydantic-settings`.
`Settings` holds the `ChunkingPolicy`
rather than re-declaring `chunk_size`/`chunk_overlap`, so the grouping has one
definition.

## The limitation -> pattern table (README section, draft to review)

| Baseline limit                                                                                                 | Where it bites on LangGraph                                                       | Corrective pattern                                                                          | Step                    |
| -------------------------------------------------------------------------------------------------------------- | --------------------------------------------------------------------------------- | ------------------------------------------------------------------------------------------- | ----------------------- |
| Single-vector embeddings miss exact matches (API names, symbols, IDs, error classes)                           | querying `add_conditional_edges` or `InvalidUpdateError` by name misses the chunk | Hybrid retrieval (BM25 + vector), P9 Component 3                                            | 3                       |
| Fixed-size chunking cuts mid-unit (code fences, mdx frontmatter, signatures) -> diluted context, hallucination | truncated LangGraph code examples, incomplete answers                             | Semantic / structure-aware indexing P7; chunk size as a tuned hyperparameter                | 3 / v2                  |
| Low-value chunks (nav, footers, boilerplate) pollute top-k                                                     | match queries without adding anything                                             | Ingestion curation + reranking P10                                                          | 3                       |
| Silent ingestion failures (encoding, mis-parsed mdx, tables)                                                   | docs vanish with no alert (Payne: 21% lost to encoding)                           | Count docs at every stage + ingestion validation                                            | 1 (named) / 2 (checked) |
| Stale / contradictory / version-specific content in one shared index (issues layer)                            | an old issue contradicts the docs; LangChain/LangGraph conflation                 | Metadata + indexing at scale P8; emergent generation criteria                               | 5                       |
| No citation validation, no grounding check                                                                     | plausible answer unsupported by context                                           | Trustworthy generation P11; 3-step citation validation (Payne)                              | 5                       |
| No abstention when the corpus does not decide                                                                  | invents instead of saying "I don't know"                                          | Out-of-domain detection / abstention P11 (Yan's no-info triple)                             | 5                       |
| No measurement: cannot tell if a change helped                                                                 | everything else is blind                                                          | Harness: golden set + IR metrics + CI                                                       | 2                       |
| No cost / latency awareness                                                                                    | --                                                                                | Prompt caching P25                                                                          | 4                       |
| Everything routed through RAG; no RAG-vs-large-context threshold                                               | "write a poem", trivial version lookups                                           | Intent routing (Payne) + context-window threshold (Lakshmanan P6 sidebar; ~200K from Anthropic) | "patterns left out" box |

A short "patterns left out of v1, and why" note follows the table: contextual
retrieval (P7), HyDE / query rewriting (P9), GraphRAG (P9), RAPTOR (P7), ColBERT
/ late interaction, Deep Search (P12). Each is named with its when-NOT reason
(no measured trigger yet), which is the repository's discipline made explicit.

## Edge cases

- Query with no relevant chunk: baseline still returns top-k and an answer
  (demonstrates the no-abstention limit). Behavior is asserted as current, not
  treated as a bug.
- Chunk that splits a code fence: chunking produces a broken fence; asserted as
  current behavior (the chunking limit).
- Empty corpus / missing snapshot: `make index` fails loudly with a clear
  message (fetch the snapshot first).
- Missing `GEMINI_API_KEY`: the query CLI fails with a clear message; indexing
  does not need it (local embeddings).

## Test scenarios

Unit (in-process, fakes, exact outcomes):

- `test_chunking`: a document of known length and a known `ChunkingPolicy`
  yields the expected number of chunks with the expected overlap; a document
  containing a code fence yields a chunk that splits the fence (current behavior
  pinned).
- `test_prompts`: `build_rag_prompt` includes the query and every chunk's text
  in a deterministic layout; with zero chunks it still produces a prompt
  (no abstention path).

Integration (real Chroma, no LLM, exact outcomes):

- `test_retrieval`: index a small known corpus into a real (temp-dir) Chroma via
  the real embedder; a query whose answer is in one chunk returns that chunk in
  the top-k. Proves the wiring (port -> Chroma -> RetrievedChunk).

No generation eval, no IR metric, no judge (later steps). The integration test
asserts a fixed outcome, it is not a score-with-threshold eval. It runs the real
(production) embedder on a small corpus (fast; the model downloads once and is
cached) and stays LLM-free. When a later test needs generation, fake the
`LLMPort` (the lowest-level generation wrapper) and keep the real embedder and
store, per the integration definition (real out-of-process components, no LLM).

## Verification

```bash
uv sync
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest         # fast loop: unit + small-corpus integration test (real embedder + Chroma, no LLM)
make index            # full build, slow (CPU embedding on the whole corpus): occasional, not a fast-loop gate
uv run rag query "how do I add a conditional edge in LangGraph?"   # end-to-end check (needs a built index + GEMINI_API_KEY)
```

## Resolved at review (2026-06-04)

- **Generation model**: Gemini 3.1 Flash-Lite. Exact `google-genai` model id
  confirmed when wiring the adapter (find-docs).
- **Embedder**: a strong, CPU-viable small/base English retrieval model (the
  LangGraph corpus is English). Exact model picked from a current MTEB short-list
  at wiring (find-docs); the `Embedder` Port makes the "swap if too slow" a
  localized change, not a rewrite.
- **Naive chunk defaults**: 1000 chars / 200 overlap. At this size the named
  limit is *structure-blind splitting* (cutting code fences / mdx frontmatter /
  signatures mid-unit), not Payne's "too small" tutorial default (~200 chars).
  The table row and `chunking.py` comment reflect this.
- **Issues curation**: a large bounded snapshot under a single minimal quality
  bar (has a human answer, non-bot, above a small character floor), frozen at a
  pinned extraction date, committed as jsonl. No stratified selection at step 1:
  the resolved/open, version-spread, contradiction-with-docs stratification is
  deferred to step 5, where error analysis needs that targeted material. The
  messy issue content is the feature here, so volume is kept; only pure noise
  (bot-only, empty, no human answer) is dropped.

## Risks

- CPU embedding time on the full three-layer corpus. Mitigation: small model,
  batched embed, hosted-embedder fallback if a `make index` becomes too slow.
- Issues curation effort. Mitigation: bound the set; error analysis on issues
  stays at step 5, step 1 only ingests them.
- Keeping the baseline naive but not a strawman. Mitigation: every naive choice
  is a real default, named in the table with its corrective pattern.

## ADRs (write, review, and commit before running the plan)

The two ADRs record decisions this plan already settled. Write them, have Roman
review and validate them, and commit them by hand as the first commit, before
`implement-plan` runs the steps below. They are deliberately not implementation
steps: the steps run automatically with one commit each, so interleaving the
ADRs there would be artificial, and it would let the automation write decisions
that need a human review first.

Create `docs/adr/003-corpus-langgraph.md` and
`docs/adr/004-baseline-architecture.md`, following the existing ADR format (see
`docs/adr/002`): Date, Status: Accepted, Context, Decision, Alternatives
considered, Consequences. Explain why, not how. Do not modify ADRs 001 and 002
(immutable).

- `003-corpus-langgraph.md`: the three-layer LangGraph corpus (docs prose, API
  reference, bounded curated issue threads), pinned refs, regenerable via
  `make index`, vector DB gitignored, issues committed as data, one shared index
  with no metadata filtering (the pollution this causes is a named limit). Record
  the issues-curation rule (single minimal quality bar, large bounded snapshot,
  pinned extraction date) and that the committed jsonl keeps the raw fetched
  per-thread fields as provenance for step 5, unused by step 1.
- `004-baseline-architecture.md`: hexagonal-from-the-start-but-minimal (pure
  domain core, three ports, thin adapters, plain DI, synchronous). Position the
  layout against its two precedents: Lakshmanan ch.6 / Pattern 19 (Dependency
  Injection) and mcp-auditor's ports-and-closures (we use plain DI, not
  `make_node` closures, since there is no LangGraph). Read ch.6 (Pattern 19)
  before writing the ADR; be precise that P19 applies DI to mocking LLM-chain
  steps (function injection, motivated by nondeterminism / model churn /
  LLM-agnosticism), while we apply the same inject-to-isolate principle to I/O
  ports, with fakes not mocks (CLAUDE.md). Record that the architecture is
  justified by invariance at the Chroma -> pgvector swap (step 3), not by an eval
  delta.

## Implementation steps

Verification commands for every code step (from `CLAUDE.md`):
`uv run ruff format --check .`, `uv run ruff check .`, `uv run pyright`,
`uv run pytest`. Run `uv sync` first when dependencies changed.

ADRs first, by hand: the two ADRs (see the "ADRs" section above) record
decisions this plan already settled. They are written, reviewed by Roman, and
committed manually as the first commit, before `implement-plan` is launched.
They are not numbered steps: the steps below are code only, run automatically
with one commit each.

### Step 1: dependencies, domain models, ports, and the pure core (test-first)

**Files**

- Modify: `pyproject.toml` (add runtime deps), `.gitignore` (gitignore outputs)
- Create: `src/rag_to_production/domain/__init__.py`,
  `src/rag_to_production/domain/models.py`,
  `src/rag_to_production/domain/ports.py`,
  `src/rag_to_production/domain/chunking.py`,
  `src/rag_to_production/domain/prompts.py`
- Create tests (write first): `tests/unit/__init__.py`,
  `tests/unit/test_chunking.py`, `tests/unit/test_chunking_given.py`,
  `tests/unit/test_chunking_then.py`, `tests/unit/test_prompts.py`

**Do**

- `pyproject.toml`: add `dependencies = ["chromadb", "sentence-transformers",
"google-genai", "httpx"]`. No `pydantic` (config is a plain dataclass with env
  read at the composition root, resolved at review). Leave dev deps untouched.
- `.gitignore`: append `chroma/` and `snapshot/` (matching the `chroma_dir` /
  `snapshot_dir` config defaults). Keep `data/langgraph-issues.jsonl` committed.
- `domain/models.py`: the five frozen dataclasses exactly as in the "Code
  details" section: `Document`, `Chunk`, `RetrievedChunk`, `RagAnswer`,
  `IndexStats`. Keep the `source` comment on `Document` (display only, not a
  retrieval filter, named limit).
- `domain/ports.py`: the three `Protocol`s exactly as specified, synchronous:
  `EmbedderPort.embed`, `VectorStorePort.add` / `search`, `LLMPort.generate`.
  Generic ports (abstract which model/store, not what question).
- `domain/chunking.py`: `ChunkingPolicy` frozen dataclass (`chunk_size`,
  `overlap`) plus pure `chunk_document(doc, policy) -> list[Chunk]`. Fixed-size
  character window with overlap, structure-blind (no mdx/heading/code-fence
  awareness). Chunk ids derive deterministically from `document_id` + index.
- `domain/prompts.py`: pure `build_rag_prompt(query, chunks) -> str`. Stuff every
  retrieved chunk's text and the query into one instruction. No
  citation-validation, abstention, or version-disambiguation instruction (each
  absence is a named limit). Deterministic layout.
- Write the test files before the implementations; watch them fail, then
  implement. Only `test_chunking` uses given/then (it abstracts corpus/policy
  setup). `test_prompts` inlines its one-liner setup, no given/then.

**Test**

- `test_chunking`: a document of known length with a known `ChunkingPolicy`
  yields the expected number of chunks and the expected overlap between adjacent
  chunks; a document containing a code fence yields a chunk that splits the fence
  (current naive behavior pinned, not treated as a bug). Assert chunk
  `document_id`/`source` propagate from the source `Document`.
- `test_prompts`: `build_rag_prompt` output contains the query string and every
  chunk's text in the deterministic layout; with zero chunks it still returns a
  non-empty prompt (the no-abstention path).

**Verify**

- `uv sync` then the four verification commands. Expect format/lint/type clean
  and the new unit tests green.

### Step 2: config, pipeline, and fakes (unit-tested with fakes)

**Files**

- Create: `src/rag_to_production/config.py`, `src/rag_to_production/pipeline.py`,
  `tests/unit/fakes.py`
- Create test (write first): `tests/unit/test_pipeline.py`
- No `pyproject.toml` change (config is a plain dataclass, no pydantic)

**Do**

- `config.py`: `Settings` (a plain frozen dataclass)
  with `embedder_model`, `llm_model`, `chunking` (a `ChunkingPolicy`), `k`,
  `chroma_dir`, `snapshot_dir`, `docs_ref`, `langgraph_ref`, `issues_path`.
  `Settings` holds the `ChunkingPolicy`, it does not re-declare
  `chunk_size`/`overlap`. These values are the single source of the naive
  defaults the README names (e.g. 1000 chars / 200 overlap, k, the chosen
  models, the pinned refs). Env (any override, `GEMINI_API_KEY`) is read at the
  composition root (`cli.py`) and passed in, never inside `Settings` (CLAUDE.md:
  no hidden env access).
- `pipeline.py`: pure DI, ports passed as arguments.
  `index_corpus(documents, embedder, store, policy) -> IndexStats` chunks each
  document, embeds the chunks, adds them to the store, and returns per-source
  document and chunk counts. `answer_query(query, embedder, store, llm, k) ->
RagAnswer` embeds the query, searches top-k, builds the prompt, generates, and
  returns the answer with the retrieved chunks as its `retrieved_context`.
  `answer_query`
  always returns top-k and an answer even when nothing relevant exists (no
  abstention, named limit).
- `tests/unit/fakes.py`: `FakeEmbedder`, `FakeVectorStore`, `FakeLLM` as real
  in-memory implementations with deterministic, configurable behavior (fakes,
  not mocks). `FakeVectorStore` returns configured nearest chunks.
- Write `test_pipeline.py` before implementing the pipeline.

**Test**

- `test_pipeline`: `index_corpus` over a small multi-source document set returns
  `IndexStats` with the expected per-source document and chunk counts, and the
  fake store received the embedded chunks. `answer_query` returns a `RagAnswer`
  whose `retrieved_context` is the store's top-k and whose `text` is the fake LLM's
  output for the prompt built from those chunks. Include the no-relevant-chunk
  case: it still returns top-k and an answer.

**Verify**

- The four verification commands (after `uv sync` if deps changed). Expect clean
  and new unit tests green.

### Step 3: adapters, ingestion, Makefile, and the integration test

**Files**

- Create: `src/rag_to_production/adapters/__init__.py`,
  `src/rag_to_production/adapters/embedder.py`,
  `src/rag_to_production/adapters/vector_store.py`,
  `src/rag_to_production/adapters/llm.py`,
  `src/rag_to_production/ingestion/__init__.py`,
  `src/rag_to_production/ingestion/snapshot.py`,
  `src/rag_to_production/ingestion/corpus.py`,
  `src/rag_to_production/ingestion/issues.py`, `Makefile`,
  `data/langgraph-issues.jsonl` (committed curated issue threads)
- Create test (integration): `tests/integration/__init__.py`,
  `tests/integration/test_retrieval.py`,
  `tests/integration/test_retrieval_given.py`,
  `tests/integration/test_retrieval_then.py`

**Do**

- `adapters/embedder.py`: `SentenceTransformersEmbedder`, model from config, CPU,
  batched embed, implements `EmbedderPort`.
- `adapters/vector_store.py`: `ChromaVectorStore`, embedded persistent Chroma
  (dir from config, gitignored). Implements `add`/`search`, maps Chroma hits to
  `RetrievedChunk`.
- `adapters/llm.py`: `GeminiLLM`, wraps `google-genai`, model from config, API
  key from env, `generate(prompt) -> str`. Fail with a clear message when the
  key is missing.
- `ingestion/snapshot.py`: fetch `langchain-ai/docs` and `langchain-ai/langgraph`
  at the pinned ref SHAs (from config) into the gitignored snapshot dir.
  Idempotent. Empty/missing snapshot must fail loudly later in `corpus.py`.
- `ingestion/corpus.py`: walk the snapshot, yield `Document` for docs (mdx) and
  API-ref, treating mdx as plain text (frontmatter/code fences not parsed out,
  naive). Fail loudly with a clear message on missing snapshot.
- `ingestion/issues.py`: read `data/langgraph-issues.jsonl`, yield
  `Document(source="issues")` per thread.
- `data/langgraph-issues.jsonl`: a large bounded snapshot of issue threads
  passing a single minimal quality bar (has a human answer, non-bot, above a
  small character floor), frozen at a pinned extraction date, committed as data.
  No stratified selection here (deferred to step 5). See "Resolved at review".
- `Makefile`: `make index` (build the index end to end, print `IndexStats` per
  source, fail loudly on empty/missing snapshot) plus thin wrappers for test,
  lint, type matching the `CLAUDE.md` commands.
- Integration test uses given/then (it abstracts corpus + temp-dir Chroma +
  embedder setup).

**Test**

- `test_retrieval` (real temp-dir Chroma, real embedder, no LLM, exact outcome):
  index a small known corpus, a query whose answer lives in one chunk returns
  that chunk in the top-k. Proves the wiring port -> Chroma -> `RetrievedChunk`.
  This is a fixed-outcome assertion, not a score-with-threshold eval.

**Verify**

- The four verification commands. Expect clean and the integration test green
  (it downloads the embedding model on first run). `make test` / `make lint` /
  `make type` resolve.

### Step 4: CLI and the `rag` console script

**Files**

- Create: `src/rag_to_production/cli.py`
- Modify: `pyproject.toml` (add `[project.scripts]` `rag =
"rag_to_production.cli:main"`)

**Do**

- `cli.py`: `main()` dispatch with `query` and `index` subcommands, wiring the
  config, adapters, and pipeline. `query` fails with a clear message when
  `GEMINI_API_KEY` is missing; `index` does not need the key (local embeddings).
- `pyproject.toml`: register the console script so `uv run rag query ...` and
  `uv run rag index` resolve. Re-run `uv sync`.

**Verify**

- `uv sync` then the four verification commands (clean). Then the smoke checks:
  `make index` builds the index and prints `IndexStats` per source;
  `uv run rag query "how do I add a conditional edge in LangGraph?"` runs end to
  end (requires `GEMINI_API_KEY` and a built index).

### Step 5: README Getting started + step-1 section with the limitation -> pattern table

**Files**

- Modify: `README.md` (add two sections only)

**Do**

- Add a **"Getting started"** section: the runnable quickstart (`uv sync`,
  `GEMINI_API_KEY` for queries only, `make index`, `uv run rag query "..."`), a
  note that the vector store is embedded Chroma persisting to a gitignored local
  dir (no service, no Docker at this stage; a managed store behind the same port
  and a `docker-compose` stack arrive at step 3, the literal demo->production
  move), that `make index` embeds on CPU and can be slow on the full corpus, and
  that the corpus is fetched from pinned refs so the build is reproducible.
- Add a "Step 1: the baseline and why it breaks" section. Open it with one
  sentence attributing the P6-P12 pattern catalog to Lakshmanan & Hapke,
  _Generative AI Design Patterns_ (with a link), since the table and the note
  cite pattern numbers that are otherwise opaque to an outside reader. State
  plainly that the baseline retrieval is single-vector embeddings (Pattern 7,
  Semantic Indexing) and that "basic" describes the overall simplicity, not
  keyword retrieval: we start here because most teams equate RAG with "a vector
  DB and nothing else", which is exactly the starting point whose limits we name.
  Then the
  limitation -> pattern table from the plan verbatim, followed by the short
  "patterns left out of v1, and why" note (contextual retrieval P7, HyDE / query
  rewriting P9, GraphRAG P9, RAPTOR P7, ColBERT / late interaction, Deep Search
  P12, each with its when-NOT reason). Do not touch the existing
  problem/method/roadmap/relationship/conventions sections.

**Verify**

- `uv run ruff format --check .` and `uv run ruff check .` still clean (no code
  changed). Visually confirm only the two new sections were added, the quickstart
  commands match the Makefile and console script, and the table matches the naive
  defaults named in `config.py`.
