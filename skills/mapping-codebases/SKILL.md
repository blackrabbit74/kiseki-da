---
name: mapping-codebases
description: "Explains an unfamiliar repository through verified entry points, data flows, module responsibilities, and working conventions. Use for onboarding or understanding where behavior lives; not for automatically rewriting architecture or installing persistent project instructions."
---

# Mapping Codebases

## Purpose

Explain how the code actually works.

## Deliverable

Return an evidence-linked code map, execution trace, conventions, and starting points.

Done when: the requested behavior can be followed from entry to effects.

Stop and report when: a missing component prevents tracing a boundary. Continue independent work and identify the blocked action.

## Inputs

Repository, manifests, tests, configuration, and reader question.

## Decision rules

- Infer architecture from execution paths, not names alone.
- Trace a representative request through validation, logic, storage, and response.
- Distinguish documented commands from successfully executed commands.

## Required procedure

1. Inspect entry points and configuration without generated dependencies.
2. Trace the relevant flow and neighboring implementations.
3. Explain extension points with source locations.

## Constraints (set by: operator)

Do not write persistent rules or refactor unless requested. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
