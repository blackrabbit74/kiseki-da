---
name: allocating-agent-budgets
description: "Assess remaining execution budget and allocate model or task effort within explicit spending and quality constraints. Use for run budgeting, warning thresholds, or model allocation decisions; this does not purchase credits, change user-selected models silently, or infer account quotas from local estimates."
---

# Allocating Agent Budgets

## Purpose

Assess remaining execution budget and allocate model or task effort within explicit spending and quality constraints.

## Deliverable

Return budget scope and period, recorded and estimated spend, remaining capacity, proposed allocation, and enforcement limits.

Done when: the allocation fits the stated ceiling or exposes its shortfall, with uncertainty and quality tradeoffs explicit.

Stop and report when: a hard user budget is exhausted or next-action spending cannot be bounded; stop all work covered by that budget. Only actions demonstrably outside it may continue. Identify the specific budget-blocked action.

## Inputs

User budget, period and currency, usage records, current pricing when needed, pending work, model constraints, and quality requirements.

## Decision rules

- Align budget and spending periods before computing utilization.
- Use user-defined thresholds; a suggested ladder is advisory until adopted.
- Choose cheaper models only when task evidence supports acceptable quality, preserving explicit model choices.

## Required procedure

1. Read actual usage and deduplicate applicable records.
2. Estimate remaining work using current verified rates and explicit uncertainty.
3. Allocate effort and identify any host-enforced cap separately from an advisory recommendation.

## Constraints (set by: operator)

Discover real usage and budget tools; do not promise a hard stop that the runtime cannot enforce or create recurring checks without request. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
