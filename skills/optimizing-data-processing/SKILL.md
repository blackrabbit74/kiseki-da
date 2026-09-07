---
name: optimizing-data-processing
description: "Improve ingestion, transformation, and extraction throughput while preserving data accounting and replayability. Use when ETL, backfills, exports, or structured-text processing are slow or unreliable; not for unmeasured speed claims or unrelated business-data interpretation."
---

# Optimizing Data Processing

## Purpose

Improve ingestion, transformation, and extraction throughput while preserving data accounting and replayability.

## Deliverable

Return a scoped pipeline change with source/target accounting, benchmark conditions, rejected records, and remaining backlog.

Done when: correctness checks and manifests agree after execution, and measured speed uses comparable workloads.

Stop and report when: source-to-target identity cannot be established for a destructive replacement; identify the blocked action and continue independent work.

## Inputs

Source and target contracts, representative records, arrival rate, checkpoints, error policy.

## Decision rules

- Separate historical backlog from live-tail growth; fast processing can still fall behind arrivals.
- Use deterministic parsers for stable structure, but route ambiguity using measured validation failures rather than invented confidence percentages.
- Batching and parallelism must retain idempotent writes and checkpoint atomicity.
- Counts alone miss substitutions; compare keys, aggregates, and representative content.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Measure extraction, transfer, transform, and loading separately; benchmark bounded alternatives and replay interrupted work before claiming completion.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
