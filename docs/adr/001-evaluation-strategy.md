# ADR 001: Evaluation Strategy

**Date:** 2026-06-03
**Status:** Accepted

## Context

This repository takes a RAG system from a naive demo to a production-ready state. The hard part of that journey is not assembling the pipeline, it is making a non-deterministic system measurable: knowing whether a change helped, catching failure modes that only appear on real questions, and keeping quality from drifting in production.

A RAG system has two components that fail in different ways and need different evaluation:

- **Retrieval** is a search problem. There is a ground truth (which documents are relevant to a query), so quality is knowable up front and measurable without an LLM.
- **Generation** is open-ended. Whether an answer is faithful, relevant, and useful is a judgment that stabilizes only by looking at outputs.

Conflating them produces the most common mistake in RAG evaluation: grading the final answer as a single number. When the answer is bad, that number cannot tell whether retrieval brought the wrong context or the model ignored good context.

## Decision

Evaluation is the backbone of the repository, and it runs in one direction: **measure first, add complexity only when a measurement justifies it.**

### Retrieval first, on its own

Retrieval is evaluated before the generator is involved, with information-retrieval metrics (recall@k, precision@k, MRR, NDCG), no LLM. The golden set pairs queries with the documents that should be retrieved. It is bootstrapped synthetically (take a document, extract key facts, generate the questions those facts answer) and hardened by hand. Retrieval and generation failures are then diagnosed separately: if the right context never reached the prompt, the fix is in indexing, chunking, ranking, or query handling, not in the generator.

### Generation second, with a calibrated judge

Answer quality is measured with an LLM-as-a-judge that is **validated against human labels**, not trusted out of the box. Verdicts are binary pass/fail with written critiques, not opaque numeric scales. The judge is iterated in isolation (fixed inputs, fast loop) before it gates the full pipeline, and its agreement with human judgment is tracked. Off-the-shelf eval metrics and unvalidated judge prompts are avoided: they create the illusion of measurement without the substance.

The core relationships measured are context relevance (does retrieval address the question), faithfulness (does the answer stay grounded in the retrieved context), and answer relevance (does the answer address the question).

### Criteria emerge from real failures

Domain-specific failure modes are not specified up front. They surface through error analysis on real outputs (open coding, then a failure taxonomy) and are recorded in a versioned criteria log, each criterion dated and tied to the cluster of failures that produced it. This makes criteria drift visible and falsifiable. The exception is the deterministic contract layer (output structure, hard rules) where success is knowable in advance and an assertion suffices.

### Measured deltas, not vibes

Every step is an experiment with a number attached (recall, precision, cost, latency). A pattern is added only when it beats the simpler version on the eval set. When it does not, the simpler version stays, and that negative result is published too. Knowing when not to add a pattern is the judgment this repository means to demonstrate.

## Alternatives considered

- **Evaluation-driven development (write evaluators before the feature).** Rejected as the default. LLM systems have an open-ended failure surface that cannot be anticipated, so evaluators are written for failures discovered, not failures imagined. The exception is the deterministic contract layer.
- **Generation-first evaluation.** Rejected. Retrieval is usually the weak link and is cheaper to measure. Fixing generation on top of broken retrieval wastes effort.
- **Off-the-shelf metric suites and prebuilt judge prompts.** Kept only as comparison baselines. The calibrated, in-repo judge is the measurement of record. A judge that is not validated against human labels is not trustworthy.

## Consequences

- The eval harness has two faces: a fast, LLM-free retrieval eval (the contract layer) and an LLM-as-a-judge generation eval (the quality layer). Their details are decided in the steps that introduce them.
- The retrieval eval can run cheaply and often. The generation eval costs tokens and runs on demand.
- The criteria log becomes a first-class, versioned artifact, the visible trace of how "good" is defined and how it changes.
- Each productionization step publishes a measured delta, including the steps where the more complex pattern did not win.
