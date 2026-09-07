---
name: designing-error-contracts
description: "Design or repair error contracts, retries, and failure boundaries across application languages. Use when failures are swallowed, retries cascade, or clients receive inconsistent errors; not for general code style reviews without failure-handling concerns."
---

# Designing Error Contracts

## Purpose

Design or repair error contracts, retries, and failure boundaries across application languages.

## Deliverable

Return changed handling and a matrix of caller response, retryability, observability, and recovery.

Done when: dependency failure, cancellation, and exhausted retries behave as documented.

Stop and report when: mutation idempotency is unknown for a proposed retry; identify the blocked action and continue independent work.

## Inputs

Failure examples, call graph, client contracts, time budgets, runtime versions.

## Decision rules

- Use stable codes or types rather than matching display strings.
- An ambiguous timeout may already have committed; retry only with suitable idempotency and an overall deadline.
- Preserve causal chains internally while excluding secrets from client messages.
- Propagate cancellation instead of converting it into retryable failure.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Trace production and consumption of errors, assign one retry owner, and inject failures to verify attempt counts and side effects.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
