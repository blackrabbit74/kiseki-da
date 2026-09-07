---
name: normalizing-market-data
description: "Ingest and normalize market price and volume data into a reproducible dataset suitable for analysis or similarity search. Use for OHLCV feeds and derived features; creating a vector index does not establish trading signal quality or authorize market transactions."
---

# Normalizing Market Data

## Purpose

Ingest and normalize market price and volume data into a reproducible dataset suitable for analysis or similarity search.

## Deliverable

Return raw and normalized data, schema and units, source identity, time coverage, transformation parameters, quality checks, and ingestion counts.

Done when: records reconcile to source coverage and derived values can be reproduced without future information leakage.

Stop and report when: source rights, missing timestamps, or incompatible adjustment conventions prevent valid ingestion; retain the diagnosed schema and supported subset. Continue independent work and identify the specific blocked action.

## Inputs

Instrument and venue identifiers, source API or file, timezone, interval, corporate-action adjustment policy, and target storage.

## Decision rules

- Keep raw data alongside derived features and identify split/dividend adjustment conventions.
- Use stable symbol-plus-venue-plus-time identities; handle duplicate and revised candles explicitly.
- For relative returns and rolling normalization, handle zero denominators and insufficient history; fit only on information available at that time.

## Required procedure

1. Verify current source schema, licensing/access conditions, and market session conventions.
2. Validate timestamps, ordering, OHLC relationships, missing intervals, and units before normalization.
3. Transform and store idempotently; verify record counts and sample readback, and index only when the retrieval use case warrants it.

## Constraints (set by: operator)

Do not invent missing candles, pad dimensions without a documented interface need, or confuse semantic embeddings with numeric market features. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
