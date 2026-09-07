---
name: reconciling-agent-costs
description: "Reconcile agent usage and cost records into reproducible totals and useful breakdowns. Use for session, model, or period cost analysis; local estimated spend is not an invoice, and missing tracking data is not zero usage."
---

# Reconciling Agent Costs

## Purpose

Reconcile agent usage and cost records into reproducible totals and useful breakdowns.

## Deliverable

Return reconciled totals, source and time scope, aggregation logic, currency, model or session breakdowns, and data gaps.

Done when: duplicate cumulative snapshots are resolved and totals reconcile to the retained records.

Stop and report when: records cannot support a requested period or attribution; report that limitation and compute supported totals. Continue independent work and identify the specific blocked action.

## Inputs

Usage logs or provider export, record schema, requested period and timezone, currency, and pricing provenance.

## Decision rules

- Determine whether rows are increments or cumulative snapshots; retain the latest cumulative record per stable session identity.
- A snapshot timestamp may not locate all session spending within that day; state attribution limits.
- Keep estimated charges separate from billed amounts and verify current pricing before recalculating.

## Required procedure

1. Inspect schema, malformed rows, identifiers, and timestamp semantics.
2. Deduplicate, aggregate with inspectable calculations, and reconcile category totals.
3. Report major cost drivers and uncertainties without exposing unnecessary transcript content.

## Constraints (set by: operator)

Do not fabricate missing usage, enable tracking hooks without request, or equate a quota percentage with a monetary bill. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
