---
name: planning-compatible-migrations
description: "Plans or implements transitions between software interfaces, libraries, or systems while preserving known consumer behavior. Use for deprecation, replacement, or compatibility work; not for deleting old paths because a new implementation merely compiles."
---

# Planning Compatible Migrations

## Purpose

Move consumers to a replacement with observable readiness.

## Deliverable

Return a compatibility inventory, migration steps, recovery approach, and removal criteria.

Done when: critical consumers work on the replacement and residual dependencies are explicit.

Stop and report when: an unavailable consumer or owner decision blocks its migration. Continue independent work and identify the blocked action.

## Inputs

Old and new systems, consumers, usage evidence, deadlines, and compatibility requirements.

## Decision rules

- Inventory undocumented behavior that consumers may rely on.
- Separate advisory deprecation from a binding removal date; do not invent deadlines.
- Remove old paths only after migration evidence meets agreed criteria.

## Required procedure

1. Map dependencies and critical behavior.
2. Build compatibility adapters or staged migration steps where useful.
3. Validate representative consumers and monitor remaining usage before removal.

## Constraints (set by: operator)

Do not treat announcement as completed migration or assume reversibility of data changes. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
