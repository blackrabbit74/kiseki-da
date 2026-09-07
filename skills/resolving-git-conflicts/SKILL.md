---
name: resolving-git-conflicts
description: "Resolves an in-progress merge or rebase by reconstructing both changes\u2019 intent and validating the combined behavior. Use for actual Git conflicts; not for choosing ours or theirs blindly or inventing new product behavior to silence conflict markers."
---

# Resolving Git Conflicts

## Purpose

Integrate both intended changes where compatible.

## Deliverable

Return resolved files, completed authorized operation, validation, and any tradeoffs.

Done when: conflicts are resolved through the operation and relevant combined behavior is checked.

Stop and report when: incompatible requirements require a user decision for a specific conflict. Continue independent work and identify the blocked action.

## Inputs

Git state, conflicting files, commit history, originating issues, and integration goal.

## Decision rules

- Read the common ancestor and both sides when intent is unclear.
- A textual resolution can still break semantic contracts; inspect callers and generated artifacts.
- Stage only conflict-related intended changes and continue each remaining rebase step.

## Required procedure

1. Identify the active operation and reconstruct each change’s purpose.
2. Resolve compatible intent and document unavoidable tradeoffs.
3. Run relevant checks and verify the final Git state.

## Constraints (set by: operator)

Do not stage unrelated work or prohibit recovery actions that the user authorizes. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
