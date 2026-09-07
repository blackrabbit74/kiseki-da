---
name: editing-shared-office-assets
description: "Find and precisely update shared documents, spreadsheets, or presentations while preserving their working context. Use for in-place collaborative asset edits or coordinated migrations; creating an unrelated standalone file does not require this cross-asset workflow."
---

# Editing Shared Office Assets

## Purpose

Find and precisely update shared documents, spreadsheets, or presentations while preserving their working context.

## Deliverable

Return the exact asset identity, completed changes, verification, useful links, and any unapplied draft.

Done when: the intended asset and affected sections, ranges, or slides are confirmed and resulting content is inspected.

Stop and report when: edit access or a compatible API is unavailable; prepare exact changes and identify only the blocked application step. Continue independent work and identify the specific blocked action.

## Inputs

Asset link or identifying context, requested changes, owner or folder, current structure, and sharing constraints.

## Decision rules

- Resolve similar titles by identity, owner, location, and current content rather than filename alone.
- Use document positions, explicit sheet ranges, or slide identifiers for targeted edits.
- Keep formulas, styles, and template relationships intact unless their change is requested.

## Required procedure

1. Discover supported service tools and inspect the exact asset.
2. Apply the smallest coherent edit with current revision awareness.
3. Read back affected content and render visual changes when supported; report conflicts and unverified layout.

## Constraints (set by: operator)

Do not change sharing, delete duplicates, or migrate sibling assets without authorization for those actions. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
