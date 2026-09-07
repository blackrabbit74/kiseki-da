---
name: evaluating-market-strategies
description: "Analyze market price patterns or test an explicitly defined trading hypothesis with reproducible historical evidence. Use for equities, digital assets, or strategy backtests; recognizing a chart shape does not establish predictive reliability, and analysis alone does not authorize trading."
---

# Evaluating Market Strategies

## Purpose

Analyze market price patterns or test an explicitly defined trading hypothesis with reproducible historical evidence.

## Deliverable

Return timestamped data scope, explicit pattern or strategy rules, reproducible calculations, costs and risk metrics, and out-of-sample limitations.

Done when: findings follow stated data and rules and descriptive detections are separated from validated predictive claims.

Stop and report when: data quality, execution assumptions, or access prevents a defensible result; provide the test specification and supported observations. Continue independent work and identify the specific blocked action.

## Inputs

Instrument and venue, timeframe, verified price data, strategy parameters, evaluation period, execution costs, and stated risk constraints.

## Decision rules

- Do not assign pattern reliability scores without calibration evidence.
- Prevent look-ahead and survivorship bias; choose rules before evaluating holdout periods.
- Include spread, fees, slippage, turnover, drawdown, and trade count rather than reporting returns alone.

## Required procedure

1. Verify current instrument, venue, data, and applicable rule facts from authoritative sources with date and jurisdiction.
2. Detect patterns using explicit thresholds or run a time-ordered strategy evaluation against a baseline.
3. Report sensitivity and limitations; preserve parameters and dataset identity so results can be reproduced.

## Constraints (set by: operator)

Do not infer live profitability from a backtest or promote it to trading automatically; any execution requires explicit scope and supported account controls. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
