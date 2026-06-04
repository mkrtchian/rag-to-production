# ADR 003: Corpus (LangGraph documentation, API reference, and issues)

**Date:** 2026-06-04
**Status:** Accepted

> **Correction (2026-06-04).** The LangGraph documentation prose lives in the
> `langchain-ai/docs` monorepo (`src/oss/langgraph`), not in the `langchain-ai/langgraph`
> repository. The API reference is generated from the `langchain-ai/langgraph` source
> docstrings rather than stored as static prose, so its ingestion is a later step and the
> current build covers prose and issues. The three-layer design is unchanged.

## Context

A RAG demo needs a corpus. The choice is not cosmetic. It decides whether the system is a real RAG or a strawman, whether retrieval quality can be judged, and whether the failure modes the repository studies are real or fabricated.

Four requirements shaped it:

- **RAG must be necessary, and worth it.** A corpus small enough to stuff whole into a context window makes the demo a strawman. But size is not the only test: even for a corpus that fits, cost, latency, and precision decide whether RAG is still the better choice (see the necessity test below).
- **Retrieval quality must be judgeable.** Some layer needs a clear ground truth, so retrieval can be measured with IR metrics (see [ADR 001](001-evaluation-strategy.md)).
- **Real failure material.** Another layer needs the messy content where answer quality actually drifts: stale advice, contradictions, version-specific answers. Fabricated failures would not be convincing.
- **Reproducible.** Anyone should rebuild the same index from a pinned state.

The corpus also has to be one whose domain is known well enough to tell whether an answer is good. The generation-side error analysis in ADR 001 depends on that.

## Decision

The corpus is the **LangGraph documentation, in three layers**. The documentation prose is built from a pinned ref of the `langchain-ai/docs` monorepo, restricted to the `src/oss/langgraph` subtree. The API reference layer is generated from the `langchain-ai/langgraph` source docstrings (see the correction note above and the Three layers section). The issue threads are committed as data.

It clears the necessity test on both counts. On size: Lakshmanan & Hapke's _Generative AI Design Patterns_ put the no-RAG threshold at roughly 200K tokens (Pattern 6, "RAG versus large context window"), but current frontier models ship one-to-two-million-token windows, so that figure is dated. The documentation prose alone is around 254K tokens and would fit such a window, but the committed corpus (that prose plus the full issue snapshot of 1056 threads) is around 2.5M tokens of indexed text and exceeds it, before the API reference layer is even added, so retrieval is required on size alone. On value: even for the layers that would fit, stuffing the whole context into every query is slow and expensive, and a focused chunk retrieves more precisely than a model reading millions of tokens unevenly. Long context has not retired RAG, it has raised the bar for when RAG is the simpler choice. Sizes were measured at the pinned docs ref and on the committed issue snapshot.

LangGraph fits the messy-material requirement especially well: it is a young, fast-moving framework, so its issue threads are full of stale workarounds, version-specific answers, and LangChain and LangGraph confusion, the exact content where answer quality drifts. It is also a domain the maintainer knows well enough to run error analysis on the answers (the requirement above), which is what makes the generation eval in ADR 001 feasible.

### Three layers

- **Documentation prose (mdx).** The verifiable layer. Clean text with a clear notion of which chunk answers a query, so retrieval has a ground truth and answers can be checked against an authoritative source. Sourced from `langchain-ai/docs` at `src/oss/langgraph`.
- **API reference (docstrings).** The second verifiable layer. It is generated from the `langchain-ai/langgraph` source docstrings rather than stored as static prose, so ingesting it means extracting docstrings, a heavier step deferred to a later plan. The baseline build covers prose and issues, with this layer added when that plan lands. Its absence today is a named gap, not a silent one.
- **Curated issue threads.** The messy layer. Outdated workarounds, contradictory advice, resolved versus open, answers that hold only for one version. This is where "good" drifts, and where the domain-specific generation criteria of the later steps come from (for example correctness for the wrong version, or LangChain content confused with LangGraph).

### Reproducibility

- Documentation prose is fetched from a pinned ref SHA of `langchain-ai/docs` (the `src/oss/langgraph` subtree only) and rebuilt with `make index`. Only that subtree is fetched, not the whole monorepo. The vector database is gitignored: it is regenerable, so it is not committed.
- Issue threads are committed as `data/langgraph-issues.jsonl`. GitHub issues cannot be pinned by a repository SHA the way files can, so the snapshot is committed to freeze it. The curation behind that file is itself a committed, re-runnable command (`make fetch-issues`, see `scripts/fetch_langgraph_issues.py`): re-running it produces a fresh snapshot at a new extraction date, not a bit-identical copy. Each record keeps the raw fields the GitHub fetch returns (number, url, state, labels, created and closed dates, body and comments) as provenance for later steps. The baseline reads only the text.

### Curation

A single minimal quality bar (has a non-bot human comment above a small length floor, by a non-bot author), applied to every open and closed issue, frozen at a pinned extraction date. The snapshot is the full set of threads that clear the bar, not a sample. No stratified selection at the baseline. The messy content is the point, so volume is kept and only pure noise is dropped. Targeted stratification (version spread, contradictions with the docs) is left to the step that runs error analysis on generation, where that material is actually used.

### Naive ingestion (named limits, not fixed here)

One shared index, no metadata filtering. mdx is treated as plain text, so frontmatter and code fences are not parsed out. The pollution this causes (a stale issue outranking the docs, or LangChain and LangGraph content conflated) is a named limit, corrected in later steps, not now.

### Excluded

Raw source code (around 1.6M tokens of `.py`) is not indexed. Dumping it adds low-value chunks that dilute retrieval, the anti-pattern this repository warns against. The rest of the `langchain-ai/docs` monorepo is also left out: LangChain prose (`src/oss/langchain`), integrations, and the JavaScript docs are not fetched. The LangChain and LangGraph conflation stays a named limit surfaced by the issues layer and generation, not something fabricated by dumping LangChain docs. Documentation prose, API reference (later), and curated issues only.

## Alternatives considered

- **A toy corpus.** Rejected. Small enough to fit a context window, so it makes RAG a strawman and cannot show realistic failure.
- **Large context window instead of RAG.** Rejected for this corpus. The committed corpus (around 2.5M tokens of indexed text, prose plus issues, before the API reference layer) exceeds current windows, and even where a corpus fits, chunked retrieval is cheaper and more precise for specific lookups. The threshold itself is named as a limit (not everything needs RAG).
- **Dumping the source code.** Rejected. Low-value chunks that add noise without adding answers.
- **The full LangChain corpus** (unified docs, source, and around ten thousand issues, on the order of 15 to 20M tokens). Deferred. It is a candidate for a later scale test on a much larger corpus, not the baseline.

## Consequences

- The same corpus carries both evaluation layers: the clean documentation prose (and the API reference once its layer lands) for verifiable retrieval, the issue threads for the generation quality work later.
- `make index` rebuilds the documentation prose layer from the pinned `langchain-ai/docs` ref and reads the committed issue snapshot. The API reference layer is added by a later plan (docstring extraction from the `langchain-ai/langgraph` source). The vector DB stays out of git.
- The committed issue snapshot is the one part of the corpus that cannot be regenerated identically from upstream, which is why it is frozen in the repository together with its provenance.
- The naive ingestion choices (shared index, no metadata, mdx as plain text) are deliberate starting points, each named as a limit with its corrective step.
