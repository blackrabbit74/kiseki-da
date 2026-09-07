---
name: managing-git-changes
description: "Organizes and performs requested Git commits, pull-request preparation, or history investigation using verified repository state. Use for version-control work; not for ordinary code edits, automatically publishing changes, or sweeping unrelated files into a commit."
---

# Managing Git Changes

## Purpose

Keep requested history changes precise and reviewable.

## Deliverable

Return the requested Git result, verified references, and remaining working-tree state.

Done when: the actual history or prepared PR matches the requested changes.

Stop and report when: an unresolved target or unavailable remote prevents a particular operation. Continue independent work and identify the blocked action.

## Inputs

Repository, requested operation, target refs, current changes, and project conventions.

## Decision rules

- Distinguish status or history investigation from mutation authority.
- Group commits by coherent behavior and revertability, keeping direct tests with implementation.
- Inspect staged content and upstream state; missing tracking information is not evidence of safety.

## Required procedure

1. Read status, refs, history, and relevant diffs.
2. Prepare scoped commits or PR content, or investigate history with an appropriate query.
3. Execute authorized operations and verify the resulting refs or server state.

## Constraints (set by: operator)

Preserve unrelated edits and do not infer permission for history rewriting or external publication. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
