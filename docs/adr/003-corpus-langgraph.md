# ADR 003: Corpus (LangGraph documentation, API reference, and issues)

**Date:** 2026-06-04
**Status:** Accepted

## Context

A RAG demo needs a corpus. The choice is not cosmetic. It decides whether the system is a real RAG or a strawman, whether retrieval quality can be judged, and whether the failure modes the repository studies are real or fabricated.

Four requirements shaped it:

- **RAG must be necessary, and worth it.** A corpus small enough to stuff whole into a context window makes the demo a strawman. But size is not the only test: even for a corpus that fits, cost, latency, and precision decide whether RAG is still the better choice (see the necessity test below).
- **Retrieval quality must be judgeable.** Some layer needs a clear ground truth, so retrieval can be measured with IR metrics (see [ADR 001](001-evaluation-strategy.md)).
- **Real failure material.** Another layer needs the messy content where answer quality actually drifts: stale advice, contradictions, version-specific answers. Fabricated failures would not be convincing.
- **Reproducible.** Anyone should rebuild the same index from a pinned state.

The corpus also has to be one whose domain is known well enough to tell whether an answer is good. The generation-side error analysis in ADR 001 depends on that.

## Decision

The corpus is the **LangGraph documentation, in three layers**, built from pinned upstream refs of `langchain-ai/docs` and `langchain-ai/langgraph`.

It clears the necessity test on both counts. On size: Lakshmanan & Hapke's _Generative AI Design Patterns_ put the no-RAG threshold at roughly 200K tokens (Pattern 6, "RAG versus large context window"), but current frontier models ship one-to-two-million-token windows, so that figure is dated. The documentation prose alone is around 271K tokens and would fit such a window, but the realistic three-layer corpus is around 2 to 3.5M tokens and exceeds it, so retrieval is required on size alone. On value: even for the layers that would fit, stuffing the whole context into every query is slow and expensive, and a focused chunk retrieves more precisely than a model reading a million tokens unevenly. Long context has not retired RAG, it has raised the bar for when RAG is the simpler choice. Sizes were measured through the GitHub API at the pinned refs.

LangGraph fits the messy-material requirement especially well: it is a young, fast-moving framework, so its issue threads are full of stale workarounds, version-specific answers, and LangChain and LangGraph confusion, the exact content where answer quality drifts. It is also a domain the maintainer knows well enough to run error analysis on the answers (the requirement above), which is what makes the generation eval in ADR 001 feasible.

### Three layers

- **Documentation prose (mdx) and API reference / docstrings.** The verifiable layer. Clean text with a clear notion of which chunk answers a query, so retrieval has a ground truth and answers can be checked against an authoritative source.
- **Curated issue threads.** The messy layer. Outdated workarounds, contradictory advice, resolved versus open, answers that hold only for one version. This is where "good" drifts, and where the domain-specific generation criteria of the later steps come from (for example correctness for the wrong version, or LangChain content confused with LangGraph).

### Reproducibility

- Documentation and API reference are fetched from pinned ref SHAs and rebuilt with `make index`. The vector database is gitignored: it is regenerable, so it is not committed.
- Issue threads are committed as `data/langgraph-issues.jsonl`. GitHub issues cannot be pinned by a repository SHA the way files can, so the snapshot is committed to freeze it. Each record keeps the raw fields the GitHub fetch returns (number, url, state, labels, created and closed dates, body and comments) as provenance for later steps. The baseline reads only the text.

### Curation

A single minimal quality bar (has a human answer, not bot-only, above a small length floor), a large bounded snapshot, frozen at a pinned extraction date. No stratified selection at the baseline. The messy content is the point, so volume is kept and only pure noise is dropped. Targeted stratification (version spread, contradictions with the docs) is left to the step that runs error analysis on generation, where that material is actually used.

### Naive ingestion (named limits, not fixed here)

One shared index, no metadata filtering. mdx is treated as plain text, so frontmatter and code fences are not parsed out. The pollution this causes (a stale issue outranking the docs, or LangChain and LangGraph content conflated) is a named limit, corrected in later steps, not now.

### Excluded

Raw source code (around 1.6M tokens of `.py`) is not indexed. Dumping it adds low-value chunks that dilute retrieval, the anti-pattern this repository warns against. Documentation, API reference, and curated issues only.

## Alternatives considered

- **A toy corpus.** Rejected. Small enough to fit a context window, so it makes RAG a strawman and cannot show realistic failure.
- **Large context window instead of RAG.** Rejected for this corpus. The realistic three-layer corpus (around 2 to 3.5M tokens) exceeds current windows, and even where a corpus fits, chunked retrieval is cheaper and more precise for specific lookups. The threshold itself is named as a limit (not everything needs RAG).
- **Dumping the source code.** Rejected. Low-value chunks that add noise without adding answers.
- **The full LangChain corpus** (unified docs, source, and around ten thousand issues, on the order of 15 to 20M tokens). Deferred. It is a candidate for a later scale test on a much larger corpus, not the baseline.

## Consequences

- The same corpus carries both evaluation layers: the clean docs and API reference for verifiable retrieval, the issue threads for the generation quality work later.
- `make index` rebuilds the docs and API layers from pinned refs and reads the committed issue snapshot. The vector DB stays out of git.
- The committed issue snapshot is the one part of the corpus that cannot be regenerated identically from upstream, which is why it is frozen in the repository together with its provenance.
- The naive ingestion choices (shared index, no metadata, mdx as plain text) are deliberate starting points, each named as a limit with its corrective step.
