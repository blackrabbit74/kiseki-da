---
name: designing-algorithm-pseudocode
description: "Translate behavioral specifications into implementable algorithms with explicit data structures and complexity assumptions. Use when logic must be designed before coding or an algorithmic approach needs comparison; not for full implementation or vague architecture diagrams without algorithm behavior."
---

# Designing Algorithm Pseudocode

## Purpose

Translate behavioral specifications into implementable algorithms with explicit data structures and complexity assumptions.

## Deliverable

Return pseudocode with input/output contracts, invariants, termination, complexity, and worked cases.

Done when: normal, boundary, and failure cases can be traced without inventing missing transitions.

Stop and report when: an unresolved specification choice changes algorithm correctness; identify the blocked action and continue independent work.

## Inputs

Behavioral specification, data bounds, ordering requirements, error semantics, resource constraints.

## Decision rules

- State the size variables used in complexity claims; input length and graph edge count are different dimensions.
- Choose structures from required operations, not familiar patterns.
- Make mutation and external side effects visible so atomicity is assessable.
- Separate assumptions from proven invariants and identify why loops terminate.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Decompose the specification, compare plausible approaches, then hand-trace empty, duplicate, extreme, and failure inputs against the chosen pseudocode.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
