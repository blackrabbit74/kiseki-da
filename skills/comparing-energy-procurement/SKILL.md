---
name: comparing-energy-procurement
description: "Compare energy tariffs, supplier offers, or power-purchase arrangements using load shape and total risk-adjusted cost. Use for electricity or gas procurement and demand-charge analysis; a simple unit-rate ranking or unauthorized hedge execution does not satisfy this workflow."
---

# Comparing Energy Procurement

## Purpose

Compare energy tariffs, supplier offers, or power-purchase arrangements using load shape and total risk-adjusted cost.

## Deliverable

Return normalized offer comparisons, reproducible cost scenarios, key contract risks, recommendation conditions, and source dates.

Done when: offers use the same load, period, units, and cost inclusions, with material price and volume exposure visible.

Stop and report when: missing interval data or contract terms prevents a defensible cost ranking; provide bounded scenarios for supported comparisons. Continue independent work and identify the specific blocked action.

## Inputs

Site and jurisdiction, meter intervals, bills, tariff class, contract dates, supplier offers, sustainability requirements, and risk tolerance.

## Decision rules

- Separate energy, demand, capacity, delivery, and riders; verify the actual local billing method.
- Fixed and indexed offers transfer different price, volume, and shape risks.
- For a virtual PPA, distinguish physical supply from financial settlement and examine basis and production-shape mismatch.

## Required procedure

1. Validate units, interval timing, peaks, and billing reconciliation.
2. Verify current tariffs, market inputs, and contract requirements from applicable primary sources.
3. Model base and stress cases, quantify tradeoffs, and produce a decision-ready comparison with sensitivity limits.

## Constraints (set by: operator)

Do not promise savings from annual averages or apply one market’s rules elsewhere. Comparison alone does not authorize contracts or hedges; preserve explicit execution authorization. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
