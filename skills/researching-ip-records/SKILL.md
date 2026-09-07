---
name: researching-ip-records
description: "Retrieves official patent or trademark records with reproducible queries, identifiers, dates, and status evidence. Use for portfolio, assignment, or prior-art record research; not for legal opinions about validity, infringement, or freedom to operate."
---

# Researching Ip Records

## Purpose

Establish what official intellectual-property records disclose.

## Deliverable

Return a cited record table, search log, discrepancies, and coverage limits.

Done when: status statements link identifiers to dated official evidence.

Stop and report when: official access prevents verifying a requested record. Continue independent work and identify the blocked action.

## Inputs

Jurisdiction, entities, identifiers, technology terms, dates, and record types.

## Decision rules

- Distinguish application, publication, grant, family, and assignment before counting.
- Use secondary indexes for discovery and official records for status.
- Verify current official services, schemas, and pagination at execution.

## Required procedure

1. Define fields and jurisdiction.
2. Retrieve available official records and preserve query details.
3. Resolve identifiers and reconcile status without legal conclusions.

## Constraints (set by: operator)

Absence of search results does not establish freedom to operate. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
