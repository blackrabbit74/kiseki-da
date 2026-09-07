---
name: researching-entity-connections
description: "Build a bounded sourced profile of a public entity and its relevant connections. Use when mapping people, organizations, repositories, or concepts around a seed; not for invasive personal surveillance or unlimited background investigation."
---

# Researching Entity Connections

## Purpose

Build a bounded sourced profile of a public entity and its relevant connections.

## Deliverable

Return an entity table and relationship map with evidence, dates, identity confidence, and unexpanded leads.

Done when: important edges have sources and the search boundary and unresolved identities are explicit.

Stop and report when: identity ambiguity could attach a consequential allegation to the wrong subject; identify the blocked action and continue independent work.

## Inputs

Seed identifier, purpose, authorized sources, relevance boundary, research budget.

## Decision rules

- Merge identities with corroborating identifiers, not similar names or embeddings alone.
- Distinguish ownership, employment, citation, and mere co-occurrence.
- Date affiliation evidence and favor direct public statements.
- Expand by relevance rather than because another connection exists.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Resolve the seed, set a proportional search boundary, collect claim-level evidence, and preserve conflicting or skipped leads.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
