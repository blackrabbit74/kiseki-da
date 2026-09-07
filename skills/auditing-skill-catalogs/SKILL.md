---
name: auditing-skill-catalogs
description: "Inventory and assess a bounded skill collection for discovery quality, overlap, stale guidance, and missing dependencies. Use for a full stocktake or review of changed skills; catalog inspection does not prove real invocation behavior or authorize deletion and installation."
---

# Auditing Skill Catalogs

## Purpose

Inventory and assess a bounded skill collection for discovery quality, overlap, stale guidance, and missing dependencies.

## Deliverable

Return the inspected inventory, evidence-backed findings, overlap decisions, priorities, and explicit coverage limits.

Done when: each disposition names the inspected version and a concrete quality reason, with unchanged cached results clearly labeled.

Stop and report when: a skill or required reference is inaccessible; mark that portion unreviewed rather than passing it. Continue independent work and identify the specific blocked action.

## Inputs

Requested skill roots, prior inventory, changed-file evidence, descriptions, entry points, references, and actual usage data when available.

## Decision rules

- Use content identity and scope to distinguish duplicate copies from meaningful variants.
- Incremental review may reuse unchanged results only when the relevant files and rubric remain unchanged.
- Low observed use is not evidence of low value when usage logging is incomplete.

## Required procedure

1. Enumerate only authorized roots and record discovered versus inspected files.
2. Review trigger precision, useful decisions, resource integrity, and overlapping deliverables.
3. Produce keep, revise, consolidate, or investigate recommendations with examples and a resumable inventory.

## Constraints (set by: operator)

Do not fabricate usage counts, silently remove skills, or require subagents for a routine inventory. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
