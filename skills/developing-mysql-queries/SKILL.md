---
name: developing-mysql-queries
description: "Implement and verify MySQL or MariaDB schemas, queries, indexes, and transaction behavior. Use when slow queries, lock contention, schema changes, or replica consistency need investigation; not for assuming interchangeable engine syntax or applying unreviewed production tuning."
---

# Developing Mysql Queries

## Purpose

Implement and verify MySQL or MariaDB schemas, queries, indexes, and transaction behavior.

## Deliverable

Return scoped SQL changes with engine/version, execution evidence, and lock or migration implications.

Done when: results remain correct and the relevant query or concurrency improvement is measured.

Stop and report when: the database target or recovery plan is unknown for a destructive schema change; identify the blocked action and continue independent work.

## Inputs

Engine/version, schema, query parameters, representative cardinalities, isolation level, replica use.

## Decision rules

- MySQL and MariaDB diverge; verify feature syntax on the actual engine.
- Composite indexes follow real predicate and ordering patterns, not one index per referenced column.
- SKIP LOCKED suits queue claims but can omit rows needed for accounting.
- DATETIME does not carry timezone metadata, and read replicas may lag committed writes.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Inspect plans and lock evidence, test proposed changes with representative data, and check deadlock retry, collation, and replication behavior where affected.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
