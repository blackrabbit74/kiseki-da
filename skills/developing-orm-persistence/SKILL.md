---
name: developing-orm-persistence
description: "Implement or repair JPA/Hibernate and Prisma persistence behavior with explicit query and transaction evidence. Use when entity mappings, relation loading, migrations, or ORM query performance need work; not for assuming identical semantics across ORM families or replacing the data layer."
---

# Developing Orm Persistence

## Purpose

Implement or repair JPA/Hibernate and Prisma persistence behavior with explicit query and transaction evidence.

## Deliverable

Return mappings or query changes with generated-SQL observations, data checks, and migration implications.

Done when: the intended rows and transactional effects are verified on the relevant provider.

Stop and report when: the database target is ambiguous for a migration or bulk mutation; identify the blocked action and continue independent work.

## Inputs

ORM and database versions, schema, relation cardinality, query traces, transaction scope.

## Decision rules

- JPA persistence contexts and Prisma request results have different lifecycle semantics; identify the active stack first.
- Collection fetch joins can multiply rows and interfere with pagination; test realistic cardinalities.
- Bulk operations may bypass entity callbacks or return counts instead of rows; verify the exact API behavior.
- Development migration commands may reset data; do not treat them as production deployment commands.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Inspect generated queries, implement projections or fetching deliberately, and test pagination, rollback, uniqueness, and bulk-update readback on representative data.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
