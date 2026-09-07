---
name: retrieving-biological-reference-data
description: "Retrieve biological reference records, identifiers, sequences, or first-pass database evidence with reproducible query provenance. Use for bounded genomic or protein database lookups; regulated clinical interpretation and high-throughput production pipelines require a different validated workflow."
---

# Retrieving Biological Reference Data

## Purpose

Retrieve biological reference records, identifiers, sequences, or first-pass database evidence with reproducible query provenance.

## Deliverable

Return retrieved records or sequences, stable identifiers, species and assembly, source version or access date, query parameters, and limitations.

Done when: results can be traced to the correct organism, identifier namespace, and database context.

Stop and report when: the required database or module is unavailable; return resolved identifiers and a query plan without inventing results. Continue independent work and identify the specific blocked action.

## Inputs

Biological question, species, gene or protein identifiers, sequence type, genome assembly, and desired database scope.

## Decision rules

- Resolve ambiguous symbols to stable IDs before retrieving sequences.
- Distinguish gene, transcript, and protein records and retain isoform choices.
- An enrichment or association lookup is exploratory evidence, not a causal or clinical conclusion.

## Required procedure

1. Discover available clients and verify current authoritative module and database documentation.
2. Run a small scoped query, checking assembly, sequence type, and identifier mapping.
3. Save inspectable results with tool/version, parameters, date, and database assumptions; cross-check surprising mappings.

## Constraints (set by: operator)

Do not silently upgrade a working environment or upload sensitive genomic data to external services without authorized scope. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
