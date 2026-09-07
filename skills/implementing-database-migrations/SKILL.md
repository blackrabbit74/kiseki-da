---
name: implementing-database-migrations
description: "Designs and implements schema or data migrations with engine-specific locking, compatibility, resumability, and recovery checks. Use for database evolution or backfills; not for assuming every migration is reversible or applying generic SQL safety claims without checking the engine version."
---

# Implementing Database Migrations

## Purpose

Change stored structure or data without losing integrity.

## Deliverable

Return migration artifacts, rollout order, validation queries, and recovery limitations.

Done when: schema and data invariants are checked under representative volume and deployment overlap.

Stop and report when: missing target access or recovery prerequisites prevent applying a migration. Continue independent work and identify the blocked action.

## Inputs

Engine and version, schema, data size, migration tooling, traffic, and recovery requirements.

## Decision rules

- Verify actual lock and transaction behavior for the engine and operation.
- Use expand-migrate-contract when old and new application versions overlap.
- Make large backfills bounded and resumable; preserve already-applied migration history.

## Required procedure

1. Inspect schema, consumers, and engine-specific behavior.
2. Implement staged changes and explicit backfill checkpoints.
3. Test representative data, interruption, compatibility, and recovery before authorized application.

## Constraints (set by: operator)

A down script cannot restore discarded data; document irreversible steps. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
