# rag-to-production

Taking a RAG system from demo to production: retrieval quality, evals, cost, and observability.

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)
[![Python 3.13+](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/)

> **Status: early and public.** The repo follows the roadmap below, one measured step at a time, starting at step 1. Each step lands on `main` with its measured result.

## The problem

RAG demos are easy. Production is the hard part.

Assembling a retrieval pipeline (chunk, embed, retrieve, generate) is close to a solved, commoditizing problem. Off-the-shelf platforms now do it. What does not commoditize is making a non-deterministic system reliable and measurable in production: knowing whether a change helped or hurt, catching the failure modes that only show up on real questions, and keeping quality from drifting once the system is live.

That reliability-and-measurement layer is what this repository is about. The RAG is the vehicle. The durable skill is the discipline around it: evaluation, observability, and the judgment to know when a pattern is worth its cost.

## The method

The method is evaluation-driven, and it runs in one direction: measure first, add complexity only when a measurement justifies it.

- **Retrieval first, evaluated on its own.** Retrieval is a search problem with a ground truth, so it is measured with information-retrieval metrics (recall@k, precision@k, MRR, NDCG), no LLM involved. A RAG answer can fail because retrieval brought the wrong context, or because the model ignored good context. Grading only the final answer cannot tell these apart. So retrieval gets its own eval, before the generator is even in the picture.
- **Generation second, with a calibrated judge.** Answer quality (faithfulness to the retrieved context, relevance to the question) is measured with an LLM-as-a-judge validated against human labels, not trusted out of the box. Binary pass/fail with written critiques, not opaque 1-to-5 scores.
- **Criteria that emerge from real failures.** The domain-specific failure modes (answers correct for the wrong version, refusals that should have been answers, sources that contradict each other) are not specified up front. They surface through error analysis on real outputs and get recorded in a versioned criteria log, so the way "good" drifts is visible and falsifiable.
- **Measured deltas, not impressions.** Every step is an experiment with a number attached (recall, precision, cost, latency). A delta is reported with error bars and paired comparisons on the same golden set, and the size of that set is stated, so a small change is distinguishable from noise rather than taken on faith. When a fancier pattern does not beat a simpler one on the eval set, that is a result too, and the simpler one stays.

Each step leaves durable artifacts on `main`: a section in this README, an Architecture Decision Record under [`docs/adr/`](docs/adr/), and a reproducible eval result. You read the journey on `main`. The git history carries the dated timeline.

## Roadmap

The system is brought from a deliberately naive baseline to a production-ready state in measured steps. Each step names the limitation it fixes and publishes the delta.

1. **Baseline, with its limits named.** A deliberately simple RAG (single-vector retrieval, fixed chunking) plus the table of why it breaks in production.
2. **Measurement harness: golden set, retrieval eval, CI.** A synthetic golden set, IR metrics, and the assertions-versus-evaluators split wired into CI.
3. **Retrieval quality, measured before and after.** Hybrid retrieval and reranking, applied only where the golden set shows a gap, with the delta published.
4. **Cost and latency: measured caching.** Caching, with the proof that it did not degrade eval scores.
5. **Observability and generation eval.** Open-standard instrumentation, a judge calibrated from error analysis on real outputs, and drift monitoring.

The corpus is three layers: the LangGraph documentation prose, an API reference generated from source docstrings, and a curated set of issue threads. The clean docs test verifiable retrieval. The issue threads (outdated workarounds, contradictory advice, version-specific answers) are where quality drifts, and where the emergent criteria come from.

## Getting started

```bash
uv sync                                              # install dependencies
cp .env.example .env                                 # then put your key in .env (query only, not index)
make index                                           # fetch the corpus and build the index
uv run rag query "how do I add a conditional edge in LangGraph?"
```

`make index` runs `uv run rag index`. Indexing embeds the corpus locally on CPU (sentence-transformers `BAAI/bge-small-en-v1.5`), so no API key is needed to build the index, and it can be slow on the full corpus. The query path calls Gemini (`gemini-3.1-flash-lite`), which reads `GEMINI_API_KEY` from `.env` (loaded at startup) or the shell environment, the shell taking precedence.

The vector store is embedded Chroma. It runs in-process and persists to a gitignored local directory (`chroma/`), so there is no service to run and no Docker at this stage. A managed store behind the same `VectorStorePort` and a `docker-compose` stack arrive at step 3, the literal demo-to-production move.

The corpus is fetched from a pinned upstream commit, so the build is reproducible. `make index` fetches the LangGraph documentation prose from the pinned `langchain-ai/docs` ref, extracts the API reference layer from the pinned `langchain-ai/langgraph` source ref, and reads the committed issue snapshot (`data/langgraph-issues.jsonl`, regenerable with `make fetch-issues`).

## Step 1: the baseline and why it breaks

The pattern numbers below (P6 through P12) refer to the RAG pattern catalog in Lakshmanan & Hapke, [_Generative AI Design Patterns_](https://www.oreilly.com/library/view/generative-ai-design/9798341622654/), which runs from Basic RAG (P6) to Deep Search (P12) as an escalator from demo to production.

The baseline retrieval is single-vector embeddings (Pattern 7, Semantic Indexing). "Basic" here describes the overall simplicity of the pipeline, not keyword retrieval: index, embed, retrieve top-k, generate, with fixed-size chunking and one shared index. We start here because most teams equate RAG with "a vector DB and nothing else", which is exactly the starting point whose limits we name.

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

### Patterns left out of v1, and why

Each of these is a real pattern we are not adding yet, because no measured trigger justifies its cost. Naming the reason now is the repository's measure-before-you-add discipline made explicit.

- **Contextual retrieval (P7):** adds a per-chunk LLM call to prepend context. Real cost, and no measured retrieval gap yet to justify it.
- **HyDE / query rewriting (P9):** rewrites the query before retrieval. We have no evidence the raw query underperforms, so there is nothing to fix.
- **GraphRAG (P9):** builds a knowledge graph over the corpus. Heavy ingestion machinery for multi-hop reasoning the LangGraph Q&A task does not require.
- **RAPTOR (P7):** recursive summarization into a tree. Useful for long-document synthesis, not for the lookup-style questions this corpus answers.
- **ColBERT / late interaction:** token-level matching with a larger index footprint. Hybrid retrieval (step 3) is the cheaper first move against the exact-match gap.
- **Deep Search (P12):** iterative, agentic multi-step retrieval. The top of the escalator, far past what a single-pass baseline needs.

## Relationship to mcp-auditor

[mcp-auditor](https://github.com/mkrtchian/mcp-auditor) is a separate, working tool: it runs adversarial security audits against live MCP servers. Its evaluation is not there to make a point, the tool has to be reliable to be useful. What it shares with this repository is the engineering approach: a calibrated LLM-as-a-judge validated against human labels, an in-repo eval harness, ground truth, and a judge-isolation eval for fast iteration. The same discipline, applied to two different problems (agentic security there, RAG here).

The two also show the same judgment on frameworks, applied in opposite directions. mcp-auditor's control flow is genuinely agentic (stateful subgraphs, loops, checkpointing), so it is built on LangGraph. A linear RAG pipeline needs none of that, so this repository stays plain, composable Python ([ADR 002](docs/adr/002-no-orchestration-framework-v1.md)). A framework is worth it when the problem needs it, not before.

## Conventions

Coding, testing, and architecture standards live in [CLAUDE.md](CLAUDE.md), the single source of truth for both human and AI-assisted contributions. Decisions are recorded as immutable ADRs in [`docs/adr/`](docs/adr/). Non-trivial features are planned in [`plans/`](plans/) before implementation, using the [spec-driven-dev](https://github.com/mkrtchian/spec-driven-dev) workflow.

## License

MIT. [Roman Mkrtchian](https://github.com/mkrtchian)
