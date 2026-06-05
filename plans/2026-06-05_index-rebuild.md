# Rebuild the index from scratch on each `make index`

**ADRs:** `docs/adr/003-corpus-langgraph.md` ("regenerable via `make index`"), `docs/adr/004-baseline-architecture.md` (ports, Chroma->pgvector swap thesis). No ADR change.

## Context

ADR 003 states the vector database is gitignored and "regenerable via `make index`".
"Regenerable" means re-running reproduces the index from the corpus. The current
behavior does not: `ChromaVectorStore.__init__` does `get_or_create_collection` and
`add` is a plain `add` (not `upsert`, no purge). So a second `make index` after a
corpus change re-embeds everything, re-adds the same deterministic ids (Chroma
warns and dedupes by id), and crucially leaves behind chunks whose ids the new
corpus no longer produces. The index drifts from the corpus instead of being
regenerated.

This was surfaced while verifying the new `api_ref` layer: a clean rebuild is
needed so the per-source counts and the step-2 retrieval eval reflect exactly the
pinned corpus, not an accretion of past runs.

The fix is to make indexing start from an empty store. It must be a **port-level**
operation, not a `rm -rf chroma/` in the CLI: a directory wipe hardcodes "the store
is a local directory", which breaks the ADR 004 thesis that a managed store
(pgvector) swaps in behind the same `VectorStorePort` with the same harness. A
pgvector store clears itself with `TRUNCATE`, not by deleting a folder. So the
store knows how to empty itself, behind the port.

## Approach

Add `reset()` to `VectorStorePort`. `index_corpus` calls it once at the start, so
"index a corpus" means "the store now holds exactly this corpus". The two existing
implementations get a `reset`: `ChromaVectorStore` deletes and recreates its
collection, `FakeVectorStore` clears its in-memory lists. Cost is unchanged (the
pipeline already re-embeds the whole corpus every run); only the storage is made to
match. The query path never resets.

Naming: `reset` (matches the rebuild intent). The Chroma adapter implements it by
deleting and recreating the single `corpus` collection, not via chromadb's global
`client.reset()` (which wipes the whole database and is settings-gated). A short
adapter comment makes that explicit.

## Files to modify

- `src/rag_to_production/domain/ports.py`: add `reset(self) -> None` to `VectorStorePort`.
- `src/rag_to_production/adapters/vector_store.py`: keep a `self._client`, add
  `reset`, extract collection creation into a private helper used by `__init__` and
  `reset`.
- `src/rag_to_production/pipeline.py`: `index_corpus` calls `store.reset()` first.
- `tests/unit/fakes.py`: `FakeVectorStore.reset` clears `added_chunks` / `added_embeddings`.
- `tests/unit/test_pipeline.py`: a test that re-indexing replaces the previous corpus.
- `tests/integration/test_retrieval.py` (+ `_given.py`, `_then.py`): a test that
  re-indexing a smaller corpus drops the removed document.

## What stays unchanged

- `answer_query`, `VectorStorePort.search`, `ChromaVectorStore.search` / `add`: the
  query path and the add path are untouched. `reset` is only called by `index_corpus`.
- `cli.py` `run_index`: no change. It calls `index_corpus`, which now resets, so the
  rebuild happens with no CLI edit.
- The snapshot fetch (`fetch_snapshot`, `fetch_source_snapshot`): idempotent
  per-layer caching is correct and is a separate concern from the index rebuild. Not
  touched. (A force-refetch is still `rm -rf snapshot/`, by design.)
- `IndexStats` and `_render_stats`: unchanged.
- No ADR change: this realigns the code with ADR 003's existing "regenerable" wording.

## Code details

### `domain/ports.py`

```python
class VectorStorePort(Protocol):
    def reset(self) -> None: ...

    def add(self, chunks: list[Chunk], embeddings: list[list[float]]) -> None: ...

    def search(self, query_embedding: list[float], k: int) -> list[RetrievedChunk]: ...
```

`reset` first (it runs before `add`/`search` in the index lifecycle, newspaper order).

### `adapters/vector_store.py`

```python
class ChromaVectorStore:
    def __init__(self, persist_dir: Path) -> None:
        self._client = chromadb.PersistentClient(path=str(persist_dir))
        self._collection = self._create_collection()

    def reset(self) -> None:
        # Drop and recreate the one corpus collection so a build starts clean. This
        # is per-collection, not chromadb's global client.reset() (which wipes the
        # whole database and is settings-gated).
        self._client.delete_collection(_COLLECTION_NAME)
        self._collection = self._create_collection()

    def add(self, ...) -> None: ...      # unchanged
    def search(self, ...) -> ...: ...    # unchanged

    def _create_collection(self) -> Collection:
        return self._client.get_or_create_collection(
            name=_COLLECTION_NAME,
            configuration={"hnsw": {"space": "cosine"}},
        )
```

`__init__` guarantees the collection exists, so `delete_collection` in `reset` never
hits a missing collection. (`reset` is only reached after construction.) Use the
chromadb `Collection` type for the helper's return annotation, matching strict
pyright. This requires a new import alongside the existing chromadb imports:
`from chromadb import Collection` (the module currently imports only `Metadata` from
`chromadb` and `PyEmbeddings` from `chromadb.api.types`).

### `pipeline.py`

```python
def index_corpus(documents, embedder, store, policy) -> IndexStats:
    store.reset()
    documents_per_source: Counter[str] = Counter()
    ...
```

One added line at the top. The rest of `index_corpus` is unchanged.

### `tests/unit/fakes.py`

```python
class FakeVectorStore:
    def reset(self) -> None:
        self.added_chunks.clear()
        self.added_embeddings.clear()
```

## Edge cases

- **First run, no `chroma/` yet:** `__init__` creates an empty collection, `reset`
  deletes and recreates it (still empty), `add` fills it. Correct, no special case.
- **Re-index identical corpus:** `reset` clears, then the same chunks are re-added.
  Result is identical to a first run (no duplicates, no orphans).
- **Re-index a smaller corpus:** chunks only present in the old corpus are gone
  (the drift this fixes).
- **Query path:** `run_query` / `answer_query` never call `reset`; a query against a
  built index is read-only and unaffected.
- **`reset` before any collection exists:** cannot happen through the public API
  (construction always creates the collection first). No defensive try/except (a
  case that cannot occur, per CLAUDE.md).

## Test scenarios

Unit (in-process, fakes, exact outcomes):

- `test_re_indexing_replaces_the_previous_corpus` (new, `test_pipeline.py`): index a
  corpus with one `docs` document, then index a different corpus with one `issues`
  document into the same `FakeVectorStore`; assert `added_chunks` holds only the
  second document's chunks (the first build's chunks were cleared by `reset`).
- Existing `test_pipeline` tests stay green: `reset` on a fresh `FakeVectorStore` is
  a no-op before the first `add`.

Integration (real Chroma + embedder, no LLM, exact outcome):

- `test_re_indexing_a_smaller_corpus_drops_the_removed_document` (new): index the
  three-document corpus, then re-index with only the `doc-edges` document into the
  same temp-dir store; a query about the checkpointer (whose document was removed)
  returns no chunk from `doc-checkpoint`. Without `reset`, the orphaned
  `doc-checkpoint` chunk would survive and could be retrieved, so this test
  distinguishes the fixed behavior from the broken one.
- Existing `test_query_returns_the_chunk_whose_text_answers_it` stays green
  (`index_corpus` is called once; `reset` on the fresh collection is harmless).

New given/then helpers:

- `given.only_the_edges_document()` -> `[a_corpus_with_a_distinctive_chunk()[0]]`.
  <!-- REVIEW: per CLAUDE.md "if it is just a one-liner wrapper, inline it instead". This helper is a one-line slice. It does name a domain concept (the reduced corpus), so a named given is defensible, but inlining the slice in the test is equally valid. Implementer's call; both comply. -->
- `given.a_corpus_with_a_distinctive_chunk` is reused for the full corpus (no new
  helper needed for the first index).
- `then.no_result_is_document(results, document_id)` -> asserts no retrieved chunk
  has that `document_id`.

## Verification

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
make test-unit
make test-integration
uv run pytest            # full suite green
```

End-to-end (manual, network + CPU embedding, not part of the loop): `make index`
twice in a row produces a stable per-source count (no accumulation), and after a
corpus change the counts reflect only the current corpus.

## Implementation steps

Repo root: `/home/roman/Projects/rag-to-production`. All paths absolute below are
relative to it. Test-first for the new behavior: write the failing test, watch it
fail, then implement (`CLAUDE.md` workflow).

### Step 1: add `reset` to the vector-store port, both implementations, the pipeline call, and the rebuild tests

The whole plan is one atomic, committable change: a single port method ripples to its
two implementations (`FakeVectorStore`, `ChromaVectorStore`) and its one caller
(`index_corpus`), with one unit test and one integration test. It touches 8 files but
every production edit is one to a few lines, well within a single agent's context
budget. Splitting would mean committing a port method with no caller (a broken
intermediate state), so it stays whole.

**Files**

Tests first, then production:

- Modify (tests): `tests/unit/test_pipeline.py`, `tests/unit/fakes.py`,
  `tests/integration/test_retrieval.py`, `tests/integration/test_retrieval_given.py`,
  `tests/integration/test_retrieval_then.py`.
- Modify (production): `src/rag_to_production/domain/ports.py`,
  `src/rag_to_production/adapters/vector_store.py`,
  `src/rag_to_production/pipeline.py`.

**Do**

1. In `tests/unit/test_pipeline.py`, add `test_re_indexing_replaces_the_previous_corpus`:
   build one `FakeVectorStore`, `index_corpus` a corpus of one `docs` document into it,
   then `index_corpus` a different corpus of one `issues` document into the *same*
   store. Reuse the existing `_document(doc_id, length, source)` and a
   `ChunkingPolicy(chunk_size=100, overlap=20)`. Run `make test-unit`, watch it fail
   (`FakeVectorStore` has no `reset`; `index_corpus` does not call it).
2. In `tests/unit/fakes.py`, add `FakeVectorStore.reset(self) -> None` that calls
   `self.added_chunks.clear()` and `self.added_embeddings.clear()`. (The `_nearest`
   read-path field is untouched.)
3. In `src/rag_to_production/domain/ports.py`, add `def reset(self) -> None: ...` to
   `VectorStorePort`, declared before `add` (index-lifecycle / newspaper order).
4. In `src/rag_to_production/adapters/vector_store.py`:
   - Add `from chromadb import Collection` to the existing chromadb imports.
   - In `__init__`, keep the client as `self._client = chromadb.PersistentClient(...)`
     and set `self._collection = self._create_collection()`.
   - Extract the `get_or_create_collection(name=_COLLECTION_NAME, configuration=...)`
     call into a private `_create_collection(self) -> Collection` placed below its
     callers (newspaper rule).
   - Add `reset(self) -> None` between `__init__` and `add`: `self._client.delete_collection(_COLLECTION_NAME)`
     then `self._collection = self._create_collection()`. Include the clarifying
     comment that this is per-collection, not chromadb's global settings-gated
     `client.reset()`. Leave `add`, `search`, `_to_retrieved_chunk`, `_column`
     unchanged.
5. In `src/rag_to_production/pipeline.py`, make `store.reset()` the first statement of
   `index_corpus`, before the `Counter` initialization. `answer_query` and
   `_add_chunks` are untouched.
6. In `tests/integration/test_retrieval_given.py`, add `only_the_edges_document() ->
   list[Document]` returning `[a_corpus_with_a_distinctive_chunk()[0]]` (the
   `doc-edges` document only). Reuse `a_corpus_with_a_distinctive_chunk`,
   `a_real_embedder`, `a_temp_dir_store`, `the_naive_chunking_policy` as-is.
7. In `tests/integration/test_retrieval_then.py`, add `no_result_is_document(results:
   list[RetrievedChunk], document_id: str) -> None` asserting no retrieved chunk has
   that `document_id`.
8. In `tests/integration/test_retrieval.py`, add
   `test_re_indexing_a_smaller_corpus_drops_the_removed_document(tmp_path)`: index the
   full three-document corpus into a temp-dir store, then `index_corpus` again into the
   *same* store with `given.only_the_edges_document()`. Embed a checkpointer query
   (e.g. "how does the checkpointer persist graph state?"), `store.search(..., k=3)`,
   and assert `then.no_result_is_document(results, document_id="doc-checkpoint")`.

**Test**

- Unit `test_re_indexing_replaces_the_previous_corpus`: after the two indexings,
  every `chunk.document_id` in `store.added_chunks` is the second document's id and
  none is the first's. The first build's chunks were cleared by `reset`.
- Integration `test_re_indexing_a_smaller_corpus_drops_the_removed_document`: the
  checkpointer query returns chunks, none from `doc-checkpoint` (its document was
  removed by the second, smaller index and `reset` purged the orphan). Without `reset`
  the orphaned chunk would survive and could be retrieved, so this test pins the fix.
- Regression: existing `test_index_corpus_*`, `test_answer_query_*`, and
  `test_query_returns_the_chunk_whose_text_answers_it` stay green (`reset` on a fresh
  store / collection before the first `add` is a harmless no-op).

**Verify**

- `uv run ruff format --check .` (clean), `uv run ruff check .` (clean),
  `uv run pyright` (no errors, strict), `make test-unit` (all pass including the new
  unit test).
- Before committing: `make test-integration` (real Chroma + embedder, new integration
  test passes) and `uv run pytest` (full suite green).
