---
name: implementing-scoped-changes
description: "Implements a bounded feature or ticket within an existing codebase, following established seams and validating requested behavior. Use when the work unit is already defined; not for inventing product requirements, unrelated refactoring, or automatically committing every edit."
---

# Implementing Scoped Changes

## Purpose

Complete the requested unit of engineering work.

## Deliverable

Return the implemented change, relevant verification, and any remaining acceptance gap.

Done when: the ticket’s observable behavior is implemented and checked.

Stop and report when: an unavailable dependency or essential requirement prevents part of implementation. Continue independent work and identify the blocked action.

## Inputs

Ticket or specification, repository, existing patterns, and acceptance examples.

## Decision rules

- Find an existing analog before introducing a new pattern.
- Add tests where they protect meaningful behavior; avoid tests that mirror low-impact edits.
- Keep unrelated dirty work outside the change.

## Required procedure

1. Trace the affected flow and confirm acceptance boundaries.
2. Implement the smallest coherent change including necessary integration.
3. Run proportionate checks and inspect the resulting diff.

## Constraints (set by: operator)

Do not silently expand scope or perform unrequested repository publication. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
