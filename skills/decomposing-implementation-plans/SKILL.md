---
name: decomposing-implementation-plans
description: "Turns established specifications into executable implementation tasks with file responsibilities, dependencies, and meaningful verification. Use for multi-step engineering work requiring a handoff or execution plan; not for defining an unsettled product concept or listing generic development stages."
---

# Decomposing Implementation Plans

## Purpose

Decompose specified changes into independently assessable increments.

## Deliverable

Return ordered tasks with outputs, files, dependencies, acceptance checks, and global constraints.

Done when: every requirement is covered and each task is independently assessable.

Stop and report when: an unresolved interface prevents planning dependent work. Continue independent work and identify the blocked action.

## Inputs

Specification, repository patterns, build commands, and constraints.

## Decision rules

- Split where one deliverable could be rejected independently; fold scaffolding into its feature.
- Inspect paths before naming files; label proposed files.
- Schedule risky interfaces before work that depends on them.

## Required procedure

1. Map responsibilities and existing analogs.
2. Create dependency-aware tasks tied to requirements.
3. Check coverage and specify realistic verification.

## Constraints (set by: operator)

Avoid fabricated commands, fixed minute estimates, and compulsory commits. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
