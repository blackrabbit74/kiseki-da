---
name: developing-postgresql-data
description: "Implement and verify PostgreSQL queries, schemas, indexes, and row-access rules with actual database evidence. Use when PostgreSQL persistence or query behavior needs development or repair; not for assuming hosted-provider helpers exist in every PostgreSQL installation."
---

# Developing Postgresql Data

## Purpose

Implement and verify PostgreSQL queries, schemas, indexes, and row-access rules with actual database evidence.

## Deliverable

Return SQL changes with query plans, result checks, role-specific evidence, and migration implications.

Done when: results and access boundaries remain correct and performance claims are measured.

Stop and report when: database identity or authority is unresolved for a schema mutation; identify the blocked action and continue independent work.

## Inputs

PostgreSQL version, schema, query workload, roles, RLS configuration, data distribution.

## Decision rules

- RLS tests must use the actual application role; privileged owners may bypass restrictions.
- Partial indexes require predicates the planner can establish from the query.
- BRIN usefulness depends on physical correlation, while JSON index choice depends on operators.
- EXPLAIN ANALYZE executes the statement; use suitable isolation for mutations and costly workloads.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Inspect roles and plans, implement the minimal schema or query change, and verify access, concurrency, cardinality, and migration behavior on representative data.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
