---
name: writing-implementation-specs
description: "Writes implementation specifications from settled requirements and existing code, defining behavior, interfaces, failure handling, and acceptance examples. Use when engineers need an actionable design handoff; not for open product discovery or routine edits requiring no specification."
---

# Writing Implementation Specs

## Purpose

Make intended behavior precise enough to implement.

## Deliverable

Return a specification with changed behavior, interfaces, states, acceptance examples, and unresolved choices.

Done when: important behavior has an observable outcome.

Stop and report when: a missing product decision prevents defining a behavior. Continue independent work and identify the blocked action.

## Inputs

Requirements, existing flows, consumers, and platform constraints.

## Decision rules

- Scale detail to interface and architectural change; bounded work may need only a short design.
- Separate required behavior from optional implementation choices.
- Include partial failure, retries, and compatibility when they affect outcomes.

## Required procedure

1. Trace the existing flow.
2. Describe proposed behavior and consequential alternatives.
3. Walk normal and failure cases against acceptance examples.

## Constraints (set by: operator)

Do not impose new approval ceremonies or mandatory planning chains. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
