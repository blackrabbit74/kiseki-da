---
name: finishing-development-work
description: "Prepares or executes the authorized integration path for completed branch work, preserving evidence, branch ownership, and unfinished changes. Use when deciding how finished work should be merged, proposed, or retained; not for forcing a fixed menu after the user already chose."
---

# Finishing Development Work

## Purpose

Finish development in the intended repository state.

## Deliverable

Return integration readiness, the authorized merge or PR result, or a preserved branch handoff.

Done when: the chosen outcome is verified and remaining branch or worktree state is clear.

Stop and report when: a missing integration choice prevents an external or destructive final step. Continue independent work and identify the blocked action.

## Inputs

Completed change, checks, source and target branches, existing instructions, and workspace ownership.

## Decision rules

- Resolve the real integration target rather than assuming the default branch.
- Distinguish implementation readiness from permission to publish or delete branches.
- Detached or externally managed workspaces require preserving ownership and recoverable references.

## Required procedure

1. Review change and relevant verification evidence.
2. Use the user’s chosen integration path or prepare a concrete decision.
3. Execute authorized integration and verify refs; clean up only within scope.

## Constraints (set by: operator)

Do not repeat a choice already made or delete retained work as routine cleanup. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
