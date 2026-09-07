---
name: refactoring-for-maintainability
description: "Simplifies or restructures code while preserving observable behavior and respecting established conventions. Use for readability, duplication, or localized technical debt; not for feature changes disguised as cleanup or reducing line count at the expense of clarity."
---

# Refactoring For Maintainability

## Purpose

Reduce maintenance cost without changing the contract.

## Deliverable

Return a focused refactor and evidence of preserved behavior.

Done when: inputs, outputs, error behavior, side effects, and relevant ordering remain intact.

Stop and report when: unknown behavior prevents safely changing a particular section. Continue independent work and identify the blocked action.

## Inputs

Target code, pain point, existing tests, conventions, and performance constraints.

## Decision rules

- Understand side effects and error paths before moving logic.
- Extract common behavior only when differences are intentional and represented clearly.
- Prefer explicit code over clever compression; respect measured hot-path requirements.

## Required procedure

1. Identify the maintenance burden and behavior boundary.
2. Refactor in coherent steps using project idioms.
3. Check behavior and inspect the diff for accidental scope expansion.

## Constraints (set by: operator)

Do not alter tests merely to accept changed semantics. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
