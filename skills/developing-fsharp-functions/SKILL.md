---
name: developing-fsharp-functions
description: "Implement and verify F# functions and workflows using explicit domain types and meaningful properties. Use when F# behavior, discriminated unions, async workflows, or property tests need changes; not for forcing a new .NET test framework or generic C# conventions."
---

# Developing Fsharp Functions

## Purpose

Implement and verify F# functions and workflows using explicit domain types and meaningful properties.

## Deliverable

Return the F# change with examples, relevant properties, and reproducible counterexamples.

Done when: domain cases and property failures are exercised with meaningful input coverage.

Stop and report when: the target F# compiler or test runtime is unavailable; identify the blocked action and continue independent work.

## Inputs

Project target, domain types, workflow boundaries, installed test tools, representative inputs.

## Decision rules

- Use discriminated unions to expose valid states; avoid wildcard matches that silently absorb new domain cases.
- Property generators should satisfy domain preconditions, and shrinkers must preserve those constraints.
- Do not prove a function by comparing it with the same implementation rewritten in the test.
- F# Async and .NET Task have different execution behavior; tests must start and await the actual workflow.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Model success and failure cases, implement the function, and run examples plus algebraic or round-trip properties with saved seeds for failures.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
