---
name: developing-clickhouse-redis-data
description: "Implement and verify ClickHouse analytics or Redis state behavior according to each system\u2019s data and consistency model. Use when analytical schemas, ingestion, caches, locks, or stream handling need changes; not for treating ClickHouse and Redis as interchangeable relational databases."
---

# Developing Clickhouse Redis Data

## Purpose

Implement and verify ClickHouse analytics or Redis state behavior according to each system’s data and consistency model.

## Deliverable

Return scoped data changes with engine-specific correctness, restart, and performance evidence.

Done when: duplicates, expiry or merging, and relevant failure recovery match the contract.

Stop and report when: the target service or data identity is unknown for a destructive operation; identify the blocked action and continue independent work.

## Inputs

Actual engine/version, workload, key or sorting schema, delivery semantics, persistence and recovery needs.

## Decision rules

- ClickHouse replacement depends on sorting identity and merge behavior; do not promise immediate uniqueness.
- Batch ingestion and partition choice must reflect read patterns and part growth, not only throughput.
- Redis multi-step state transitions need suitable atomicity; lock release must verify ownership and expiry does not fence stale workers.
- Pub/Sub and Streams have different replay and delivery semantics; choose from the required consumer contract.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Identify the active engine, inspect schema and query patterns, implement the bounded change, and test duplicate ingestion, concurrent access, expiry/merge behavior, and restart recovery where relevant.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
