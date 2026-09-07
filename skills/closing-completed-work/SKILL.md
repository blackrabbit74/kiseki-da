---
name: closing-completed-work
description: "Close a completed document, change set, or milestone with traceable deliverables and outstanding obligations. Use when work needs a durable completion record and archival preparation; it does not equate unfinished requirements with success or automatically publish a version."
---

# Closing Completed Work

## Purpose

Close a completed document, change set, or milestone with traceable deliverables and outstanding obligations.

## Deliverable

Return a completion record linking deliverables, acceptance evidence, known gaps, dispositions, and archival locations.

Done when: completed claims match evidence and remaining obligations retain owners or explicit unresolved status.

Stop and report when: missing acceptance evidence prevents declaring a requirement complete; close independently verified portions. Continue independent work and identify the specific blocked action.

## Inputs

Agreed scope, deliverables, current status, acceptance results, version identifier when relevant, and archival conventions.

## Decision rules

- Distinguish delivered, verified, accepted-with-gap, and unfinished work.
- Use existing project records; archival should preserve retrieval and historical meaning.
- A stale audit cannot prove the current revision satisfies requirements.

## Required procedure

1. Reconcile requirements against actual artifacts and validation.
2. Record gaps and their dispositions without silently converting them to completion.
3. Update the requested status and archive references; verify links and report any publication still pending.

## Constraints (set by: operator)

Do not create tags, delete active material, or start a new milestone unless those actions are in scope. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
