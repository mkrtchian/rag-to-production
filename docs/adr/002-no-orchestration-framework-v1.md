# ADR 002: No Orchestration Framework in v1

**Date:** 2026-06-03
**Status:** Accepted

## Context

The v1 RAG pipeline is linear: index, retrieve, generate, with a measurement harness around it. A reader arriving from [mcp-auditor](https://github.com/mkrtchian/mcp-auditor), which is built on LangGraph, might expect the same framework here. This ADR records why v1 deliberately does not use one.

## Decision

v1 is plain, composable Python. No orchestration framework (LangGraph or otherwise).

An orchestration framework earns its place when control flow is non-trivial: subgraphs, checkpointing and resume, loops, adaptive branching. mcp-auditor has all of these (a subgraph per tool, resume after a crash, probe-observe-escalate chains), which is why [its ADR 001](https://github.com/mkrtchian/mcp-auditor/blob/main/docs/adr/001-why-langgraph.md) chose LangGraph. A linear RAG pipeline has none of them. Adding a graph runtime to a straight line would be complexity without measured value, the exact anti-pattern this repository is about.

LangGraph is reserved for the agentic retrieval extension (iterative, multi-hop, retrieve-reason loops), where a loop carrying state genuinely justifies it. That extension, if built, gets its own ADR.

## Alternatives considered

- **LangGraph throughout, as in mcp-auditor.** Rejected. It is over-engineering for a linear pipeline. Plain, composable parts keep the flow easy to read and change, and a framework is introduced only when control flow genuinely needs it (the agentic extension). Reaching for a graph runtime before then would be the complexity-without-value this repository argues against.
- **A RAG framework (LlamaIndex, LangChain RAG abstractions, or similar).** Rejected for v1. These hide the very mechanics the repository exists to make visible: chunking, indexing, ranking, the retrieval-versus-generation split. The pipeline is built from small, inspectable parts. Individual libraries (a vector store, a BM25 implementation, a reranker) are used behind ports, but no end-to-end framework drives the flow.

## Consequences

- The pipeline is built from small functions and explicit calls, readable top to bottom.
- A thin LLM and embedding interface sits behind a port, so the provider can be swapped without touching pipeline logic. The exact client library is decided in the step that introduces generation.
- This decision is scoped to the v1 linear pipeline. If agentic retrieval is built later, it gets its own ADR introducing LangGraph for that part, and the linear pipeline still stays plain Python.
