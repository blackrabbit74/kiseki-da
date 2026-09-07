---
name: addressing-review-feedback
description: "Evaluates code-review feedback against repository behavior, implements supported corrections, and documents evidence-based disagreements. Use when responding to review findings; not for blindly accepting every suggestion or posting replies without explicit authorization."
---

# Addressing Review Feedback

## Purpose

Resolve review feedback without introducing regressions.

## Deliverable

Return implemented resolutions, checks, and any unresolved or disputed items.

Done when: each feedback item has an evidence-backed disposition.

Stop and report when: an ambiguous requirement blocks the dependent correction. Continue independent work and identify the blocked action.

## Inputs

Review comments, current code, intended behavior, and existing constraints.

## Decision rules

- Check whether feedback applies to the current revision.
- Group related findings when one fix changes their assumptions.
- If a suggestion conflicts with supported behavior, explain the conflict and propose a narrower remedy.

## Required procedure

1. Read all feedback and trace affected code.
2. Implement sound corrections and verify relevant behavior.
3. Reconcile each item with changes or technical reasoning.

## Constraints (set by: operator)

Continue independent clear items; do not require all comments to be clarified first. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
