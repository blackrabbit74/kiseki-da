---
name: developing-kotlin-workflows
description: "Implement and verify Kotlin workflows with explicit nullability, coroutine ownership, and platform behavior. Use when Kotlin functions, coroutines, flows, or their tests need changes; not for requiring Kotest, MockK, or a universal coverage threshold."
---

# Developing Kotlin Workflows

## Purpose

Implement and verify Kotlin workflows with explicit nullability, coroutine ownership, and platform behavior.

## Deliverable

Return code changes with focused examples and deterministic asynchronous tests where relevant.

Done when: success, failure, cancellation, and collection lifetime match the intended contract.

Stop and report when: a required platform target or coroutine test runtime is unavailable; identify the blocked action and continue independent work.

## Inputs

Kotlin version, Gradle configuration, coroutine scopes, platform targets, existing tests.

## Decision rules

- Propagate CancellationException; broad result or exception wrappers can accidentally swallow cancellation.
- Cold Flow executes per collector; shared flows require explicit lifecycle and replay decisions.
- Virtual time helps only when code uses the injected test scheduler rather than hard-coded dispatchers.
- Mutable properties and Java platform types can invalidate comfortable nullability assumptions.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Trace scope ownership, implement the change, and test cancellation, collector restart, ordering, and relevant platform boundaries without real-time sleeps.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
