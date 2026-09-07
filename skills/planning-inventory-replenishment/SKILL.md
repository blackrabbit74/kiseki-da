---
name: planning-inventory-replenishment
description: "Plan inventory replenishment or production quantities from demand, supply timing, and operational constraints. Use for safety stock, seasonal buying, stockout risk, or changed lead times; descriptive sales reporting alone does not require ordering recommendations."
---

# Planning Inventory Replenishment

## Purpose

Plan inventory replenishment or production quantities from demand, supply timing, and operational constraints.

## Deliverable

Return demand assumptions, inventory position, proposed quantities and dates, capacity or purchasing constraints, and service-versus-stock tradeoffs.

Done when: recommendations account for open supply, commitments, lead-time uncertainty, pack sizes, and the stated service objective.

Stop and report when: inventory definitions or critical supply dates cannot be reconciled; hold dependent orders while calculating supported scenarios. Continue independent work and identify the specific blocked action.

## Inputs

Demand history, stockouts and promotions, on-hand and on-order records, commitments, lead times, MOQ/pack sizes, and capacity.

## Decision rules

- Sales during stockouts may understate demand; flag censoring before fitting forecasts.
- Define inventory position without double-counting backorders and commitments.
- Intermittent demand and variable lead times may invalidate a normal-demand safety-stock formula.
- Use time-ordered holdouts; percentage errors become unstable near zero demand.

## Required procedure

1. Reconcile SKU, location, units, and available supply.
2. Choose a demand model suited to pattern and data, then evaluate bias and forecast uncertainty.
3. Translate demand into dated replenishment or production scenarios, round to feasible constraints, and show exception priorities.

## Constraints (set by: operator)

Do not release purchase orders or change production schedules unless authorized; distinguish planning estimates from firm supplier commitments. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
