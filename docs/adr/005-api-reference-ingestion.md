# ADR 005: API reference layer ingestion (docstring extraction)

**Date:** 2026-06-05
**Status:** Accepted

## Context

[ADR 003](003-corpus-langgraph.md) decided a three-layer LangGraph corpus and named
the API reference layer as a deferred gap. This ADR records how that layer is
ingested, and supersedes its "deferred to a later plan" status.

The API reference is not static prose. Upstream generates it at site-build time
from the `langchain-ai/langgraph` source-package docstrings, so ingesting it means
reading the source. The ADR 003 boundary still holds: documented public signatures
and their docstrings are the verifiable contract layer and are in scope, raw `.py`
bodies are excluded (low-value chunks, the Payne anti-pattern). Extracting the
documented public surface is not a raw-source dump.

## Decision

Build the layer by **static extraction of the public API and its docstrings from a
pinned `langchain-ai/langgraph` source ref**, regenerable via `make index`.

- **Static, not introspective.** The source is parsed statically rather than by
  importing the package and reading a live object graph. No third-party code runs
  at ingestion and the output is reproducible from the pinned ref.
- **Public API only.** Only the surface upstream marks public (its `__all__` and
  package re-exports) is extracted, not every symbol in every module. This keeps the
  layer at the verifiable-contract register and clear of the excluded raw-source
  dump. The resolution mechanics belong to the plan, not this ADR.
- **One Document per public symbol**, identified by its public import path
  (`langgraph.graph.StateGraph`, not the internal defining module). A class carries
  its public methods. This gives the retrieval eval a clean unit: one query, one
  symbol.
- **Plain text, not a mkdocstrings re-render.** Signature plus docstring. The naive
  baseline does not reproduce the upstream rendered markdown.
- **Scope: the graph-building public surface**, the `langgraph` core plus the
  `prebuilt` and `checkpoint` packages, matching the Python reference rendered
  upstream. LangChain is not fetched, so the LangChain and LangGraph conflation
  stays a named limit surfaced by the issues layer.
- **Regenerable, not committed.** The source is pinned by commit SHA and rebuilt by
  `make index`. This is the opposite of the issue snapshot, which is committed only
  because GitHub issues cannot be pinned by a repository SHA.

## Alternatives considered

- **Import the package and introspect.** Rejected. It runs third-party code at
  ingestion and depends on the installed environment, neither safe nor reproducible.
- **Mirror the upstream mkdocstrings/Sphinx render.** Rejected. It couples the build
  to documentation tooling for no benefit at the baseline, which needs the text, not
  rendered markdown.
- **Commit the layer as data.** Rejected. The source is SHA-pinnable, so the layer
  is regenerable. Committing it would freeze a derivative for no reason.
- **One Document per module.** Rejected. A re-exported symbol's defining module is
  invisible to the user, who imports it from the package path. Per-symbol Documents
  carry the public path and give the eval a clean unit.
- **Every non-underscore symbol in every module.** Rejected. It pulls in internal
  classes never meant for use, the noise that borders the excluded raw-source dump.

## Consequences

- The corpus now carries all three layers of ADR 003. `make index` reports
  per-source counts including `api_ref`.
- A `langchain-ai/langgraph` source ref returns to the configuration, for source
  docstrings, a different purpose than the documentation-prose fetch that ADR 003
  moved to the `langchain-ai/docs` monorepo.
- Named limits, consistent with the naive baseline. The text is plain, not the
  upstream render. Resolution is best-effort and static, so a dynamic export is not
  followed. The structure-blind chunker can still split a large symbol mid-method.
- This decision supersedes the deferral in ADR 003. The vector database stays out
  of git.
