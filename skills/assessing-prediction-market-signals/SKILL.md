---
name: assessing-prediction-market-signals
description: "Assess prediction-market prices as evidence for a specified decision or product signal. Use for market-implied forecasts, dashboards, or oracle research; venue prices are not objective probabilities and this workflow does not recommend or execute bets."
---

# Assessing Prediction Market Signals

## Purpose

Assess prediction-market prices as evidence for a specified decision or product signal.

## Deliverable

Return event definitions, timestamped quotes, venue and resolution evidence, signal-quality assessment, independent comparisons, and integration conditions.

Done when: the market outcome matches the intended question and liquidity, spread, freshness, and resolution limits are explicit.

Stop and report when: the relevant market or resolution terms cannot be verified; withhold its implied probability and analyze other evidence. Continue independent work and identify the specific blocked action.

## Inputs

Decision context, event and horizon, candidate venues, current quotes and order-book evidence, and non-market sources.

## Decision rules

- Similar event titles may hide different resolution dates, authorities, or outcome definitions.
- Thin liquidity, wide spreads, stale quotes, or concentrated incentives weaken the signal.
- A market’s last traded price may differ from an executable quote and from a calibrated probability.

## Required procedure

1. Verify current venue terms, market state, resolution rules, and jurisdictional access limitations with primary sources.
2. Record prices with timestamps and assess market quality against the exact decision.
3. Compare independent evidence and recommend usable, weak, or unsuitable signal status with freshness and fallback conditions.

## Constraints (set by: operator)

Do not silently create betting access or automated alerts; recommendations concern information use, not financial positions. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
