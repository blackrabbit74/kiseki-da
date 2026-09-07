---
name: implementing-retrieval-knowledge-bases
description: "Implement document retrieval, vector search, or source-linked knowledge graphs with measured quality and durable storage semantics. Use for RAG or knowledge infrastructure; searching an existing collection for one answer does not require building a database."
---

# Implementing Retrieval Knowledge Bases

## Purpose

Implement document retrieval, vector search, or source-linked knowledge graphs with measured quality and durable storage semantics.

## Deliverable

Return the ingestion and query implementation, source metadata, schema, update behavior, retrieval evaluation, and storage validation.

Done when: queries retrieve relevant permitted evidence and updates, deletions, and restarts preserve intended identities and relationships.

Stop and report when: a required embedding or database interface is unavailable; provide schema and local fixtures while marking that integration unverified. Continue independent work and identify the specific blocked action.

## Inputs

Corpus and access boundaries, query examples, source structure, embedding model, existing store, and quality or latency constraints.

## Decision rules

- Keep embedding model, dimension, normalization, and distance metric compatible across writes and queries.
- Use source-linked stable chunk identities and apply permission filtering before exposing results.
- For code graphs, distinguish type-only imports from runtime dependencies to avoid phantom execution cycles.
- Measure approximate search against a meaningful baseline before choosing indexing or compression.

## Required procedure

1. Verify current client APIs and define chunk, entity, and relation provenance.
2. Implement idempotent ingestion, updates, deletion, and filtered retrieval using the existing stack.
3. Evaluate representative relevant and no-answer queries; verify persistence and inspect false positives, stale records, and source links.

## Constraints (set by: operator)

Do not adopt advertised speedups as measurements or treat embedding similarity as factual truth. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
