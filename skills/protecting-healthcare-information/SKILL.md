---
name: protecting-healthcare-information
description: "Design or assess healthcare information controls across data classification, access, audit, and exposure paths. Use for clinical application privacy or regulatory gap reviews; generic security advice and a technical checklist alone do not establish legal compliance or certification."
---

# Protecting Healthcare Information

## Purpose

Design or assess healthcare information controls across data classification, access, audit, and exposure paths.

## Deliverable

Return data-flow and role mappings, control changes or findings, evidence of isolation and logging behavior, and unresolved regulatory applicability.

Done when: sensitive flows and actor permissions are explicit and material control claims have test or configuration evidence.

Stop and report when: jurisdictional applicability or data access is unresolved; qualify legal conclusions and continue technical analysis with synthetic examples. Continue independent work and identify the specific blocked action.

## Inputs

Jurisdiction and organization role, data categories, care setting, architecture, access model, audit design, retention rules, and available evidence.

## Decision rules

- Separate clinical data, workforce information, and billing data under the actual applicable definitions.
- Test facility and tenant isolation beyond the UI, including privileged and export paths.
- Audit logs can expose sensitive data themselves; minimize content and verify who can modify or bypass them.

## Required procedure

1. Verify current authoritative privacy and healthcare requirements for the actual jurisdiction and as-of date.
2. Trace data through APIs, logs, URLs, browser storage, exports, backups, and third parties.
3. Implement or recommend proportionate controls and test unauthorized access, record isolation, redaction, and audit integrity.

## Constraints (set by: operator)

Do not label a system compliant from row-level security alone or upload real patient data to an unapproved service. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
