---
name: evaluating-adaptive-runtime-learning
description: "Evaluate or implement a bounded adaptive-learning component in an existing agent runtime using reproducible benchmarks. Use when learned routing, adapter updates, or retained task patterns need technical validation; not for claiming to train the assistant itself or automatically enabling continuous learning."
---

# Evaluating Adaptive Runtime Learning

## Purpose

Evaluate or implement a bounded adaptive-learning component in an existing agent runtime using reproducible benchmarks.

## Deliverable

Return the scoped runtime change or experiment with baseline, held-out outcomes, overhead, and regression evidence.

Done when: quality and cost claims use comparable measurements and retention failures remain visible.

Stop and report when: the claimed learning component or training interface cannot be found in actual code or tools; identify the blocked action and continue independent work.

## Inputs

Runtime repository, component API, authorized training data, baseline tasks, compute budget.

## Decision rules

- Discover implementation and supported interfaces before assuming SONA, LoRA, or a pattern store exists.
- Separate retrieval improvements, prompt changes, and parameter updates; they are different mechanisms.
- Evaluate retained capabilities as well as newly trained tasks to detect forgetting.
- Training-set success does not establish generalization, and reduced trainable parameters do not directly prove runtime savings.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Inspect the real component, define a bounded comparison, implement or run only the authorized experiment, and measure held-out quality, latency, memory, and prior-task regressions.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
