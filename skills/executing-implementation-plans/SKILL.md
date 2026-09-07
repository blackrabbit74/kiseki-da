---
name: executing-implementation-plans
description: "Carries out an established engineering plan through dependency-aware tasks, checkpoints, and evidence-backed completion. Use when a written plan is ready for implementation; not for blindly following stale instructions or substituting task tracking for completed software."
---

# Executing Implementation Plans

## Purpose

Execute the plan while keeping reality and status aligned.

## Deliverable

Return implemented deliverables, task status, justified deviations, and verification evidence.

Done when: all in-scope tasks meet their acceptance conditions or have precise blockers.

Stop and report when: a missing decision or inaccessible dependency blocks specific tasks. Continue independent work and identify the blocked action.

## Inputs

Plan, source specification, current repository state, and project checks.

## Decision rules

- Review plan assumptions against current code before editing.
- Treat a failed test as diagnostic work, not an automatic reason to abandon the whole plan.
- When evidence invalidates a step, preserve intent and record the necessary adjustment.

## Required procedure

1. Map tasks to current files and dependencies.
2. Execute ready tasks and checkpoint completed outputs.
3. Verify integration and reconcile every acceptance item with evidence.

## Constraints (set by: operator)

Do not impose worktree creation, delegation, or branch integration rituals. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
