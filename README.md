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

The corpus is the LangGraph documentation, API reference, and a curated set of issue threads. The clean docs test verifiable retrieval. The issue threads (outdated workarounds, contradictory advice, version-specific answers) are where quality drifts, and where the emergent criteria come from.

## Relationship to mcp-auditor

[mcp-auditor](https://github.com/mkrtchian/mcp-auditor) is a separate, working tool: it runs adversarial security audits against live MCP servers. Its evaluation is not there to make a point, the tool has to be reliable to be useful. What it shares with this repository is the engineering approach: a calibrated LLM-as-a-judge validated against human labels, an in-repo eval harness, ground truth, and a judge-isolation eval for fast iteration. The same discipline, applied to two different problems (agentic security there, RAG here).

The two also show the same judgment on frameworks, applied in opposite directions. mcp-auditor's control flow is genuinely agentic (stateful subgraphs, loops, checkpointing), so it is built on LangGraph. A linear RAG pipeline needs none of that, so this repository stays plain, composable Python ([ADR 002](docs/adr/002-no-orchestration-framework-v1.md)). A framework is worth it when the problem needs it, not before.

## Conventions

Coding, testing, and architecture standards live in [CLAUDE.md](CLAUDE.md), the single source of truth for both human and AI-assisted contributions. Decisions are recorded as immutable ADRs in [`docs/adr/`](docs/adr/). Non-trivial features are planned in [`plans/`](plans/) before implementation, using the [spec-driven-dev](https://github.com/mkrtchian/spec-driven-dev) workflow.

## License

MIT. [Roman Mkrtchian](https://github.com/mkrtchian)
