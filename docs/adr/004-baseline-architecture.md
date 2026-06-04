# ADR 004: Baseline Architecture

**Date:** 2026-06-04
**Status:** Accepted

## Context

[ADR 002](002-no-orchestration-framework-v1.md) ruled out an orchestration framework for the linear v1 pipeline. This ADR records the structure used instead, and why it is hexagonal from the first commit even though the baseline is small.

The pipeline does I/O at three points: it embeds text, it reads and writes a vector store, and it calls an LLM. Everything else (chunking, prompt construction, assembling the answer) is pure computation. The risk in a small RAG is letting the two kinds of code blur: an embedding call inside the chunker, a store query inside the prompt builder. That blur is what makes a system hard to test and hard to change.

## Decision

The baseline is **hexagonal, but minimal**: a pure domain core, three ports for the I/O it actually does, thin adapters behind them, and plain dependency injection.

### Module layout

```
domain/      models, ports (Protocols), chunking, prompts   # pure, no I/O
adapters/    embedder, vector store, LLM                     # one adapter per port
ingestion/   corpus snapshot fetch and issue loading
pipeline.py  index_corpus and answer_query, ports passed in
config.py    a frozen Settings dataclass (values only)
cli.py       the composition root: builds adapters, reads env, wires everything
```

`domain/` is the inside of the hexagon and depends on nothing outside it. `adapters/` and `cli.py` are the outside. Dependencies point inward: the domain declares the ports, the adapters implement them.

### Pure domain core

Chunking, prompt construction, and the domain models are pure functions and frozen dataclasses. Same inputs, same output, no I/O. They are unit-tested with no out-of-process dependency.

### Three ports

`Embedder`, `VectorStore`, and `LLM` are `Protocol`s, one per I/O boundary the baseline uses. The ports are generic: they abstract which model or store is used, not what question is asked (the generic-port lesson from mcp-auditor's [hexagonal architecture ADR](https://github.com/mkrtchian/mcp-auditor/blob/main/docs/adr/002-hexagonal-architecture.md): a port abstracts which model answers and the infrastructure, not what question is asked, so prompts stay pure domain functions). They are synchronous: a linear batch-index plus single-query pipeline has no concurrency need, unlike mcp-auditor's async graph.

### Plain dependency injection

Ports are passed as arguments. No framework, no container, no node-factory closures (mcp-auditor injects ports into its LangGraph nodes through `make_*` factory closures, for example `make_judge_response(llm)`. There is no LangGraph here, see [ADR 002](002-no-orchestration-framework-v1.md)). The composition root (the CLI) builds the adapters, reads the environment, and passes everything in. Configuration is a frozen dataclass holding values only. Environment access, including the API key, happens explicitly at the composition root and is passed down, never read implicitly inside the config object, so no I/O is hidden behind a constructor.

### Tested with fakes, not mocks

The ports are filled with fakes (real in-memory implementations) in unit tests, and with the real adapters in integration tests. This follows the repository testing standards: assert observable outcomes, not call sequences.

This is the same inject-to-isolate idea as the Dependency Injection pattern (Pattern 19) in Lakshmanan & Hapke's _Generative AI Design Patterns_, applied to a different boundary. Pattern 19 injects functions to mock the steps of an LLM chain, motivated by nondeterminism, model churn, and staying model-agnostic. Here the same principle is applied to the I/O ports, with fakes rather than mocks.

### Justified by invariance, not by a delta

A refactor produces no eval delta, so the architecture is not justified by one. Its payoff shows up later, at the swap from embedded Chroma to a managed pgvector store: the same port, the same harness, the same numbers, and a change confined to one adapter. Proof by invariance.

## Alternatives considered

- **Direct calls, no ports.** Rejected. Hides I/O inside the domain, forces network and model calls into every test, and turns the later store swap into a rewrite instead of a localized change.
- **A RAG framework that owns the flow.** Rejected in ADR 002, and again here on testability: it hides the mechanics the repository exists to show.
- **`pydantic-settings` reading the environment at construction.** Rejected. It hides environment access behind an object, against the rule that I/O and env access stay explicit. Config stays a plain dataclass, the environment is read at the composition root.
- **Async ports.** Rejected. The baseline batch-indexes once and answers one query at a time. Async would be machinery without a need. It can be revisited if a later step introduces real concurrency.

## Consequences

- The domain core is fully unit-testable with fakes: no network, no model download.
- Swapping the embedded vector store for a managed one later is a single adapter change behind an unchanged port, validated by unchanged harness numbers.
- The provider behind each port (embedding model, store, LLM) is chosen in the step that introduces it, without touching pipeline logic.
- The structure stays small: three ports, thin adapters, plain functions. It is hexagonal for testability and swap-ability, not for ceremony.
