# API reference layer ingestion (docstring extraction)

**ADRs:** `docs/adr/005-api-reference-ingestion.md` (new, write before implementing; supersedes the "deferred" status in `docs/adr/003-corpus-langgraph.md` without editing it)

## Context

ADR 003 decides a three-layer LangGraph corpus: documentation prose (verifiable),
API reference / docstrings (verifiable), curated issue threads (messy). The
baseline (`plans/2026-06-03_baseline-rag-and-limits.md`) shipped two of the three.
`Source = Literal["docs", "api_ref", "issues"]` already exists in `domain/models.py`,
but nothing produces `"api_ref"` yet. This plan fills that gap.

Why it was deferred (load-bearing). The LangGraph API reference is not static
prose. In the `langchain-ai/docs` monorepo, `src/oss/reference/langgraph-python.mdx`
is an ~83-byte stub: the rendered reference is generated at site-build time from
the `langchain-ai/langgraph` source-package docstrings. So ingesting this layer
means extracting docstrings from the LangGraph source, a heavier step than
fetching prose, which is why ADR 003 split it out.

Scope boundary held. "API reference / docstrings" is part of the verifiable
(contract) layer and is in scope. Dumping raw `.py` source is explicitly excluded
(ADR 003 "Excluded": low-value chunks, Payne anti-pattern). Extracting public
signatures plus docstrings is not a raw-source dump: we keep only the curated
public surface and the documentation it carries, not the implementation bodies.

Discipline (baseline spirit). Still the naive baseline: no eval or measurement
here, just ingest the layer and name its limits. Pure core, ports for I/O, value
objects over loose scalars, English, test-first for logic, functions under ~20
lines, files under ~300, fakes not mocks, given/then only where it abstracts.

## Decisions settled before this plan

1. **Extraction mechanism: static `ast` parse.** Parse a pinned source checkout
   with Python `ast` (no import, no introspection, no executing third-party code,
   reproducible). We do not mirror the upstream mkdocstrings/Sphinx rendering: a
   small `ast` extractor producing plain `signature + docstring` text is the
   naive-baseline-consistent choice. Not rendering mkdocstrings markdown is a
   named limit.
2. **Source provenance: pinned `langchain-ai/langgraph` source SHA.** Re-introduces
   a langgraph repo reference in config, for a different purpose than the dropped
   docs fetch (source docstrings, not prose). SHA
   `43682f0830f312822f18206dfa18c599becbff38` (confirmed downloadable 2026-06-05,
   see "Confirmed against the snapshot").
3. **Regenerable, not committed.** Source CAN be SHA-pinned (unlike GitHub issues),
   so the `api_ref` layer is regenerable via `make index` from the pinned ref, NOT
   committed as data. (Issues are committed only because they cannot be SHA-pinned.)
4. **Package scope: core + prebuilt + checkpoint.** `libs/langgraph` (StateGraph,
   Pregel, graph, types, constants, func), `libs/prebuilt` (`create_react_agent`,
   `ToolNode`, `tools_condition`), `libs/checkpoint` (`BaseCheckpointSaver`,
   savers). Matches the public Python reference rendered upstream. LangChain is not
   fetched (the LangChain/LangGraph conflation stays a named limit, not fabricated).
5. **Public surface: re-exports / `__all__` from public entry points.** Extract only
   the curated public API, not every non-underscore symbol in every module. A
   **public entry point** is a package `__init__.py` or any module that declares
   `__all__` (confirmed against the real tree: `langgraph.types`, `langgraph.constants`,
   `langgraph.errors` are public non-init modules carrying `__all__`). For each entry
   point the public names are its `__all__` if present, else (for an `__init__`
   without `__all__`) the non-underscore top-level defs and re-export imports. That
   non-underscore fallback is load-bearing, not optional: `langgraph.checkpoint.base`
   and `langgraph.checkpoint.memory` are inits with NO `__all__`, so an `__all__`-only
   rule would silently drop the entire checkpoint public API. Internal definition
   modules (for example `langgraph.graph.state`, `langgraph.prebuilt.tool_node`) are
   not enumerated, they are only render targets reached by following a re-export.
   This keeps the layer at the verifiable-contract register and avoids dumping
   internal classes (which would border on the excluded raw-source dump).
6. **Granularity: one Document per public symbol.** A class Document bundles its
   public methods' signatures and docstrings. `id` is the public qualified name
   (`langgraph.graph.StateGraph`), exactly how users import and query, which gives
   clean ground truth for the step-2 retrieval eval. A large class can still exceed
   one chunk and be split mid-method by the naive fixed-size chunker: the same
   structure-blind chunking limit the baseline already owns, named not fixed here.

## Approach

A pure `ast`-based extractor plus a thin I/O walker, mirroring the prose layer's
split (`corpus.load_docs` does I/O, chunking/prompts are pure). Source is fetched
into the existing gitignored snapshot dir by reusing the snapshot adapter's
private helpers. A new `SourceCheckout` value object names the source ref and its
package subtrees, parallel to `ProseSource`. The new layer joins the corpus in
`cli._load_corpus` and its snapshot is fetched in `cli.run_index`. Per-source
stats already flow through unchanged.

The one genuinely heavier piece is resolving the public surface across files: a
public name in a package `__init__` (for example `StateGraph` in
`langgraph/graph/__init__.py`'s `__all__`) is defined in a sibling module
(`langgraph/graph/state.py`) and re-exported. Resolution is done statically from
the import statements, then the defining module is parsed for the symbol node.

## Files to create

```
src/rag_to_production/ingestion/api_reference.py   # pure extractor + I/O walker
docs/adr/005-api-reference-ingestion.md            # new ADR (by hand, reviewed)
tests/unit/test_api_reference.py
tests/unit/test_api_reference_given.py
tests/unit/test_api_reference_then.py
```

## Files to modify

- `src/rag_to_production/domain/models.py`: add the `SourceCheckout` value object;
  update the `Source` comment (the layer now ships, no longer "not yet produced").
- `src/rag_to_production/config.py`: add `api_ref: SourceCheckout` default; update
  the stale "current build covers prose + issues" comment.
- `src/rag_to_production/ingestion/snapshot.py`: add `fetch_source_snapshot` and a
  pure `is_extractable_source` predicate, reusing the existing private helpers.
- `src/rag_to_production/cli.py`: fetch the source snapshot in `run_index`; add
  `load_api_reference` to `_load_corpus`.
- `README.md`: drop the two "API reference layer ... arrives in a later step"
  mentions (lines 39 and 54), state the build now covers three layers.
- `tests/unit/test_snapshot.py`: add cases for `is_extractable_source`.

ADR 003 is not touched: it is immutable and accepted, and the new ADR 005
supersedes its "deferred" status (the proper mechanism for accepted ADRs). Its
existing dated correction was for a factual error in the decision itself, not the
case here.

## Files that stay unchanged

- `docs/adr/001`, `docs/adr/002`, `docs/adr/003`, `docs/adr/004` (immutable,
  accepted). ADR 005 supersedes ADR 003's "deferred" status without editing it.
- `pipeline.py`, `chunking.py`, `prompts.py`, `ports.py`, the adapters: the new
  layer produces ordinary `Document(source="api_ref")` values that flow through
  the existing index path untouched. `_render_stats` already iterates sources, so
  `api_ref` appears in `make index` output with no change.
- `corpus.py`, `issues.py`, `redaction.py`. The `api_ref` text is upstream-authored
  API documentation, not user-submitted, so `scrub_secrets` is not applied to it
  (considered and declined: docstrings do not carry leaked user keys the way issue
  bodies do; revisit only if a real leak appears).
- `data/`: nothing committed (the layer is regenerable).
- Issues and docs ingestion: unchanged.

## Code details

### `domain/models.py`: `SourceCheckout`

```python
@dataclass(frozen=True)
class SourceCheckout:
    """Pinned origin of the API-reference layer: the package subtrees `paths` of `repo` at `ref`.

    Each path is a `langgraph` package directory (its basename is the top-level
    package, its parent is the prefix stripped to derive module qualnames).
    """

    repo: str
    ref: str
    paths: tuple[str, ...]
```

Parallel to `ProseSource`, but `paths` is plural: the public API spans three
package subtrees that all install into the one `langgraph` namespace.

Update the `Source` comment to drop "not yet produced" (the layer ships here).

### `config.py`: `api_ref` default

```python
api_ref: SourceCheckout = field(
    default=SourceCheckout(
        repo="langchain-ai/langgraph",
        ref="43682f0830f312822f18206dfa18c599becbff38",  # confirmed downloadable 2026-06-05
        paths=(
            "libs/langgraph/langgraph",
            "libs/prebuilt/langgraph",
            "libs/checkpoint/langgraph",
        ),
    )
)
```

The SHA and the three subtree paths were confirmed against the real tree on
2026-06-05 (see "Confirmed against the snapshot" below): the SHA downloads,
`prebuilt` and `checkpoint` are separate libs (not merged into core), and all
three `libs/*/langgraph` dirs exist. Update the existing `docs` field comment that
says the build "covers prose + issues".

### `ingestion/snapshot.py`: source fetch

Reuse the existing `_wanted_blobs`, `is_wanted_path`, `_download_blob` (already
private helpers taking a `paths` tuple). Add a public entry point and a pure
predicate, leaving `fetch_snapshot` (prose) untouched.

```python
def fetch_source_snapshot(snapshot_dir: Path, checkout: SourceCheckout) -> None:
    target = snapshot_dir / "source"
    if target.exists() and any(target.iterdir()):
        return
    for blob_path in _wanted_blobs(checkout.repo, checkout.ref, checkout.paths):
        if not is_extractable_source(blob_path):
            continue
        _download_blob(checkout.repo, checkout.ref, blob_path, target / blob_path)


def is_extractable_source(blob_path: str) -> bool:
    if not blob_path.endswith(".py"):
        return False
    segments = blob_path.split("/")
    return "tests" not in segments and "test" not in segments
```

`is_extractable_source` keeps only `.py` and drops test trees, so we fetch the
package source, not the whole repo. Idempotent (skips when `snapshot/source`
already populated), like the prose fetch.

### `ingestion/api_reference.py`: extractor

Newspaper order: public I/O walker first, pure helpers below it.

```python
def load_api_reference(snapshot_dir: Path, checkout: SourceCheckout) -> Iterator[Document]:
    root = snapshot_dir / "source"
    _require_snapshot(root)                      # same loud-failure shape as load_docs
    modules = _read_modules(root, checkout)      # module qualname -> ModuleSource
    for symbol in public_symbols(modules):
        yield Document(id=symbol.qualname, text=symbol.text, source="api_ref")
```

Pure core (operates on already-read source text, no I/O, no imports of target code):

```python
@dataclass(frozen=True)
class ModuleSource:
    source: str
    is_package: bool   # came from an __init__.py


@dataclass(frozen=True)
class PublicSymbol:
    qualname: str   # public import path, "langgraph.graph.StateGraph"
    text: str       # qualname header + signature + docstring (+ public methods for a class)


def public_symbols(modules: dict[str, ModuleSource]) -> list[PublicSymbol]:
    """Resolve every public entry point's surface, then render each symbol.

    A public entry point is a package `__init__` OR a module declaring `__all__`.
    For each, `public_api` gives name -> defining module; the symbol's Document id
    is the ENTRY POINT qualname + name (the public import path the user types,
    `langgraph.graph.StateGraph`), while the TEXT is rendered from the defining
    module (`langgraph.graph.state`). `modules` values carry source plus an
    is_package flag and an has_all flag so this can pick entry points and so
    `public_api` can apply the init-only non-underscore fallback. A symbol exposed
    at two public paths yields one Document per path (no dedup, named limit).
    `_read_modules` must fail loudly on a duplicate module qualname, not overwrite.
    """


def public_api(qualname: str, source: str, is_package: bool) -> dict[str, str]:
    """Public name -> defining module qualname, from `__all__` and re-export imports.

    Honors `__all__` when present (a name defined locally maps to `qualname`
    itself, a re-exported name maps to its import source). When `__all__` is absent
    and `is_package`, falls back to the non-underscore top-level defs and re-export
    imports (load-bearing for `langgraph.checkpoint.base` / `.memory`, which have no
    `__all__`); a non-package module without `__all__` is not an entry point and is
    never passed here. Resolves BOTH absolute
    (`from langgraph.graph.state import StateGraph`) and relative
    (`from .state import StateGraph`) imports: relative against `qualname`, absolute
    taken as the literal module qualname. A `__getattr__` dynamic export is ignored
    when `__all__` is present (the constants module pairs both). Names whose defining
    module is outside the snapshot (for example imported from langchain_core) are
    dropped.
    """


def render_symbol(module_qualname: str, name: str, module_source: str) -> str | None:
    """The qualname header plus the rendered Class/Function node, or None if `name`
    is not a Class/Function def in `module_source` (a bare constant or type alias)."""
```

Signature rendering uses `ast.unparse` (Python 3.13) on the node's args and
return annotation, then drops the body. For a class: `class Name(bases):` plus the
class docstring plus each public (non-underscore) method's signature and docstring.

`_read_modules` walks `root`, reads each `.py`, and computes the module qualname
by stripping the matching checkout path's parent prefix (so
`snapshot/source/libs/langgraph/langgraph/graph/state.py` becomes
`langgraph.graph.state`, and `.../__init__.py` becomes the package qualname).

Qualname collision across libs. All three subtrees install into the one
`langgraph` namespace, so a top-level `libs/<lib>/langgraph/__init__.py` in more
than one lib would map to the same qualname `langgraph` and the last write into the
dict would silently win. Confirmed 2026-06-05: the monorepo uses a PEP 420 namespace
package (no top-level `langgraph/__init__.py` in any lib, each contributes distinct
submodules like `langgraph.graph`, `langgraph.prebuilt`, `langgraph.checkpoint`), so
the keys do not collide. `_read_modules` must still not silently overwrite if a
future ref reintroduces one: detect a duplicate qualname and fail loudly.

### Document text format (deterministic, naive plain text)

```
langgraph.graph.StateGraph

class StateGraph(Generic[StateT]):
    """Short class docstring..."""

    def add_node(self, ...) -> Self:
        """..."""

    def add_conditional_edges(self, ...) -> Self:
        """..."""
```

Plain text, not mkdocstrings markdown (named limit). The qualname header puts the
exact symbol token in the chunk text, which is the content hybrid retrieval will
exploit at step 3, but we do not optimize for that here.

### Wiring (`cli.py`)

- `run_index`: after `fetch_snapshot(...)`, add
  `fetch_source_snapshot(settings.snapshot_dir, settings.api_ref)`.
- `_load_corpus`: add
  `load_api_reference(settings.snapshot_dir, settings.api_ref)` to the `chain(...)`.

## Edge cases and named limits

- **Unresolvable public names** (star imports, `__getattr__`-only exports, names
  imported from outside the snapshot such as langchain): dropped, not crashed.
  Confirmed 2026-06-05 that LangGraph uses explicit `__all__` / re-export imports on
  its public entry points (the `constants` module pairs `__all__` with a deprecation
  `__getattr__`, which is ignored since `__all__` is authoritative). Named limit: the
  curated surface is best-effort static resolution.
- **Public constants / type aliases** (no Class/Function def): skipped by
  `render_symbol` (no signature or docstring to carry). Confirmed harmless on
  `START` / `END`, which `langgraph.constants` and `langgraph.graph` both export.
  Named limit.
- **Same symbol exposed at two public paths** (a re-export plus the defining module's
  own `__all__`): one Document per path, no dedup. Minor, named limit.
- **`@overload` functions**: the implementation def is rendered, overload stubs
  ignored. Named limit.
- **Large class split mid-method** by the fixed-size chunker: same structure-blind
  chunking limit as the baseline, named not fixed.
- **Not mkdocstrings**: plain text, not the upstream rendered markdown. Named limit.
- **Missing/empty source snapshot**: `load_api_reference` fails loudly with a clear
  message (fetch first via `make index`), same shape as `load_docs`.

## Test scenarios

Unit (in-process, pure extractor and the tmp-file walker, exact outcomes). Use
given/then: `test_api_reference.py` reads as a spec, given.py holds sample source
trees, then.py holds assertions.

- A public module function yields a Document whose `id` is its qualname and whose
  text contains the rendered `def` signature and the docstring.
- A public class yields one Document including its public methods' signatures and
  docstrings, and excluding a `_private` method.
- `__all__` is honored: a non-underscore symbol absent from `__all__` yields no
  Document.
- A re-export resolves with the public id: `graph/__init__.py` with
  `__all__ = ["StateGraph"]` and `from langgraph.graph.state import StateGraph`
  yields one Document whose id is the exporting path `langgraph.graph.StateGraph`
  (not `langgraph.graph.state.StateGraph`), with text rendered from `state.py`'s
  class.
- A public non-init module with `__all__` (types.py-style): its `__all__` names
  defined locally yield Documents at `langgraph.types.<name>`.
- A package `__init__` WITHOUT `__all__` (checkpoint/base-style): the non-underscore
  fallback enumerates its local defs and re-export imports, excluding underscore
  names. An internal definition module without `__all__` and not an init is NOT
  enumerated on its own (only reached as a re-export render target).
- A public name imported from outside the snapshot (for example
  `from langchain_core.x import Y`) yields no Document and no error.
- A public bare constant / type alias yields no Document.
- Signature rendering preserves annotations and defaults (via `ast.unparse`).
- `load_api_reference` over a tmp-dir package tree yields the expected Document ids
  and text (exercises `_read_modules` qualname derivation, no network).
- Missing snapshot: `load_api_reference` raises a clear `FileNotFoundError`.

`test_snapshot.py`: `is_extractable_source` is True for a `.py` under a package,
False for a non-`.py`, False for a file under a `tests/` segment.

No network-bound automated test (consistent with the prose layer, where only the
pure `is_wanted_path` predicate is unit-tested and the real fetch is covered by
`make index`). No eval, no IR metric, no judge (later steps).

## Verification

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
uv run pytest                 # unit + integration, all green
make index                    # full build: now prints docs, api_ref, issues per source
uv run rag query "what does StateGraph.add_conditional_edges do?"   # end-to-end (needs index + GEMINI_API_KEY)
```

`make index` output gains an `api_ref` line in the per-source stats, the simplest
confirmation the layer is indexed.

## Confirmed against the snapshot (2026-06-05)

Checked directly against `langchain-ai/langgraph` at the pinned SHA (GitHub trees +
raw blobs), so the extractor is built for the real layout, not a guess:

- The SHA `43682f0830f312822f18206dfa18c599becbff38` downloads (HTTP 200). `libs/`
  holds separate `langgraph`, `prebuilt`, `checkpoint` libs (prebuilt and checkpoint
  are NOT merged into core). The three `libs/*/langgraph` package dirs exist.
- No top-level `langgraph/__init__.py` in any lib (PEP 420 namespace package), so
  the three subtrees contribute distinct submodule qualnames and do not collide.
- Public surface is `__all__` + explicit re-export imports (absolute, for example
  `from langgraph.graph.state import StateGraph`), confirming the absolute-import
  resolution is required. Public non-init modules carry `__all__` too
  (`langgraph.types`, `langgraph.constants`, `langgraph.errors`).
- `langgraph.checkpoint.__init__` is empty, and `langgraph.checkpoint.base` /
  `.memory` are inits with NO `__all__` (they define locally and re-export). This is
  why the non-underscore fallback for `__init__`s is load-bearing, not optional, for
  the checkpoint scope.

Only item left to eyeball at implementation: the exact non-underscore public set the
fallback yields for the two checkpoint inits (a sanity check that it captures
`BaseCheckpointSaver` / `InMemorySaver` and does not leak obvious internals). No
network step is required during the coded steps; the unit tests use synthetic source.

## ADR work (write, review, commit by hand before implement-plan)

Mirrors the baseline plan: decision docs are written, reviewed by Roman, and
committed manually before the automated code steps run.

- **`docs/adr/005-api-reference-ingestion.md`** (new, Accepted): records the
  mechanism decisions of this plan, the why not the how. Static `ast` extraction
  (no executing third-party code, reproducible) over import-introspection or
  mirroring upstream mkdocstrings; public surface via re-exports / `__all__` (the
  curated contract surface, not a raw-source dump, ADR 003 "Excluded" upheld);
  one Document per public symbol (clean retrieval ground truth); package scope core
  + prebuilt + checkpoint; pinned source SHA, regenerable via `make index`, not
  committed (contrast with issues, which are committed because they cannot be
  SHA-pinned); plain-text rendering, not mkdocstrings, as a named limit. Follow the
  existing ADR format (Date, Status, Context, Decision, Alternatives considered,
  Consequences). Reference ADR 003 from ADR 005 (one-directional supersede), do not
  edit ADR 003.

## Implementation steps

Three steps, one commit each. The ADR work (ADR 005, new) is done by hand and
committed before these automated steps run (see "ADR work" above). The steps below
assume it is in place.

Standard verification loop for every code step (`CLAUDE.md`), run after each
meaningful change since `make test-unit` is effectively instant:

```bash
uv run ruff format --check .
uv run ruff check .
uv run pyright
make test-unit
```

Before committing each step, also run `make test-integration` and the full
`uv run pytest`. Use absolute paths throughout; the repo root is
`/home/roman/Projects/rag-to-production`.

**Network facts already confirmed (2026-06-05).** The SHA, the three
`libs/*/langgraph` paths, the PEP 420 namespace layout, and the `__all__` /
re-export style were checked against the real tree (see "Confirmed against the
snapshot"). The coded steps below need no network: the unit tests use synthetic
source. The one thing to eyeball during step 2 is the non-underscore fallback's
output for the two `__all__`-less checkpoint inits (does it capture
`BaseCheckpointSaver` / `InMemorySaver` without leaking obvious internals), which a
quick `make index` per-source count surfaces.

### Step 1: `SourceCheckout` value object, config default, source snapshot fetch

**Files**:
- modify `/home/roman/Projects/rag-to-production/tests/unit/test_snapshot.py` (add `is_extractable_source` cases)
- modify `/home/roman/Projects/rag-to-production/src/rag_to_production/domain/models.py` (add `SourceCheckout`, update the `Source` comment)
- modify `/home/roman/Projects/rag-to-production/src/rag_to_production/config.py` (add `api_ref` field, update the stale `docs` comment)
- modify `/home/roman/Projects/rag-to-production/src/rag_to_production/ingestion/snapshot.py` (add `fetch_source_snapshot`, `is_extractable_source`)

**Do** (tests first):
1. In `test_snapshot.py`, add three plain assertions for the new pure predicate
   `is_extractable_source` (no given/then needed, it is a one-liner predicate like
   the existing `is_wanted_path` tests in this file). Watch them fail (import error).
2. In `models.py`, add the frozen `SourceCheckout` dataclass exactly as in "Code
   details": fields `repo: str`, `ref: str`, `paths: tuple[str, ...]`, with the
   docstring given there. Place it next to `ProseSource` (newspaper order, value
   objects grouped). Update the `Source` comment (lines 4-5) to drop "not yet
   produced": the `api_ref` layer ships in this plan.
3. In `config.py`, add the `api_ref: SourceCheckout` field with the default from
   "Code details" (repo `langchain-ai/langgraph`, the confirmed SHA, the three
   confirmed `libs/*/langgraph` paths), import `SourceCheckout` alongside
   `ProseSource`. Edit the `docs` field comment so it no longer says the build
   "covers prose + issues" (it now covers three layers).
4. In `snapshot.py`, add `fetch_source_snapshot(snapshot_dir, checkout)` and the
   pure `is_extractable_source(blob_path)` predicate exactly as in "Code details".
   Reuse `_wanted_blobs`, `_download_blob` (already take a `paths` tuple); import
   `SourceCheckout`. Leave `fetch_snapshot` (prose) untouched. Target dir is
   `snapshot_dir / "source"`; the fetch is idempotent (skip when already populated)
   and filters to `.py` outside `tests`/`test` segments.

**Test**:
- `is_extractable_source("libs/langgraph/langgraph/graph/state.py")` is `True`.
- `is_extractable_source("libs/langgraph/README.md")` is `False` (not `.py`).
- `is_extractable_source("libs/langgraph/tests/test_graph.py")` is `False`
  (under a `tests/` segment); also `False` for a `.../test/...` segment.

No automated test for `fetch_source_snapshot` itself (network-bound, mirrors the
prose layer where only the pure predicate is unit-tested and the real fetch is
covered by `make index`).

**Verify**: the four-command loop, all clean and green.

### Step 2: the `ast` extractor (pure core + I/O walker, test-first)

**Files**:
- create `/home/roman/Projects/rag-to-production/tests/unit/test_api_reference_given.py` (sample source trees / module dicts)
- create `/home/roman/Projects/rag-to-production/tests/unit/test_api_reference_then.py` (assertions on Documents and `PublicSymbol`s)
- create `/home/roman/Projects/rag-to-production/tests/unit/test_api_reference.py` (the spec)
- create `/home/roman/Projects/rag-to-production/src/rag_to_production/ingestion/api_reference.py` (extractor)

**Do** (test-first, the heart of the plan):
1. Write the given/then spec in `test_api_reference.py` covering every scenario in
   "Test scenarios" below, then the helpers in `_given.py` / `_then.py`. Put sample
   source as small inline Python strings in `_given.py` (a `state.py` defining
   `StateGraph` with a public method and a `_private` one, a `graph/__init__.py`
   with `__all__` and a re-export, a module with a bare constant, a module importing
   a name from `langchain_core`). Extract into given/then only where it abstracts
   (per `CLAUDE.md`); inline trivial one-liners. Watch the suite fail.
2. Implement `api_reference.py` in newspaper order: public I/O walker
   `load_api_reference(snapshot_dir, checkout)` first, then the pure core below it.
   - Pure core: `PublicSymbol` (frozen dataclass `qualname`, `text`),
     `public_symbols(modules)`, `public_api(init_qualname, init_source)`,
     `render_symbol(module_qualname, name, module_source)`, and the
     `ast.unparse`-based signature rendering (drop the body, keep args + return
     annotation; for a class: `class Name(bases):`, class docstring, then each
     public non-underscore method's signature + docstring). Signatures as in
     "Document text format".
   - `public_api` honors `__all__` when present, else non-underscore names from
     top-level `from ... import Name` and top-level class/func defs; resolves both
     absolute and relative re-export imports (relative against `init_qualname`);
     drops names whose defining module is outside the snapshot.
   - `render_symbol` returns `None` for a name that is not a Class/Function def
     (bare constant, type alias).
   - I/O helpers below the core: `_read_modules(root, checkout)` (walk `root`, read
     each `.py`, derive the module qualname by stripping the matching checkout
     path's parent prefix, distinguish package `__init__`s from plain modules per
     the `public_symbols` docstring, and fail loudly on a duplicate qualname rather
     than silently overwrite), and `_require_snapshot(root)` (same loud-failure
     shape and message style as `corpus._require_snapshot`).
   - Do NOT import or execute target code: static `ast` only. Keep functions under
     ~20 lines, file under ~300, all English.

**Test** (exact outcomes, in-process, no network):
- A public module function yields a `Document` whose `id` is its qualname and whose
  text contains the rendered `def` signature and the docstring.
- A public class yields one `Document` including its public methods' signatures and
  docstrings, and excluding a `_private` method.
- `__all__` is honored: a non-underscore symbol absent from `__all__` yields no
  `Document`.
- A re-export resolves: `graph/__init__.py` with `__all__ = ["StateGraph"]` and
  `from langgraph.graph.state import StateGraph` yields one `Document`
  `langgraph.graph.StateGraph` rendered from `state.py`'s class.
- A public name imported from outside the snapshot (`from langchain_core.x import Y`)
  yields no `Document` and no error.
- A public bare constant / type alias yields no `Document`.
- Signature rendering preserves annotations and defaults (via `ast.unparse`).
- `load_api_reference` over a `tmp_path` package tree (write the `_given.py` sample
  files to disk under `snapshot/source/libs/.../langgraph/...`) yields the expected
  `Document` ids and text, exercising `_read_modules` qualname derivation.
- Missing/empty snapshot: `load_api_reference` raises `FileNotFoundError` with a
  clear "fetch first" message.

**Verify**: the four-command loop, all clean and green.

### Step 3: wiring and README

**Files**:
- modify `/home/roman/Projects/rag-to-production/src/rag_to_production/cli.py` (fetch source snapshot in `run_index`, add `load_api_reference` to `_load_corpus`)
- modify `/home/roman/Projects/rag-to-production/README.md` (lines ~40 and ~54: three layers)

**Do** (glue and docs, no test-first dance per `CLAUDE.md`):
1. In `cli.py`: import `fetch_source_snapshot` and `load_api_reference`. In
   `run_index`, after `fetch_snapshot(settings.snapshot_dir, settings.docs)`, add
   `fetch_source_snapshot(settings.snapshot_dir, settings.api_ref)`. In
   `_load_corpus`, add `load_api_reference(settings.snapshot_dir, settings.api_ref)`
   to the `chain(...)`. `_render_stats` already iterates sources, so `api_ref`
   appears with no further change.
2. In `README.md`: the line at ~40 ("the API reference layer ... arrives in a later
   step") and the line at ~54 ("The API reference layer, generated from source
   docstrings, arrives in a later step") both become statements that the build now
   covers three layers (docs prose, API reference, issue threads). Keep the
   LangChain/LangGraph conflation limit intact, it is unrelated. ADR 003 is not
   edited (immutable), ADR 005 records and supersedes its "deferred" status.

**Verify**: the four-command loop clean. Then the end-to-end gate (needs network and
`GEMINI_API_KEY`, not part of the unit loop):

```bash
make index   # per-source stats now print an api_ref line alongside docs and issues
uv run rag query "what does StateGraph.add_conditional_edges do?"
```

## Risks

- **Monorepo layout drift** at the pinned SHA (lib paths, prebuilt or checkpoint
  merged into core). Mitigation: the SHA is pinned and the layout was confirmed
  against the fetched tree on 2026-06-05 (see "Confirmed against the snapshot"), so
  it cannot drift under us.
- **Dynamic exports** defeating static resolution. Mitigation: resolve what is
  statically reachable, name the rest as a limit. Confirmed that LangGraph public
  entry points use explicit `__all__` / re-export imports.
- **Fetch volume** (one HTTP GET per `.py` blob, three packages). Mitigation:
  `.py`-and-not-tests filter, idempotent snapshot cached under `snapshot/source`.
