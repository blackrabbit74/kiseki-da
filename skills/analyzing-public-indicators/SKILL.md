---
name: analyzing-public-indicators
description: "Collects and analyzes economic or social indicator series from official statistical sources, preserving units, revisions, frequency, and publication lag. Use for dated indicator overviews or trend comparisons; not for personalized investment advice or causal claims from correlation alone."
---

# Analyzing Public Indicators

## Purpose

Make indicator trends comparable.

## Deliverable

Return sourced series, transformations, trend findings, and limitations.

Done when: comparisons specify period, unit, adjustment, vintage, and missing data.

Stop and report when: an unavailable series prevents a comparison. Continue independent work and identify the blocked action.

## Inputs

Jurisdiction, indicators, horizon, frequency, and available series.

## Decision rules

- Do not mix nominal and real values, levels and rates, or seasonal adjustments.
- Align observation periods; disclose release lag and provisional figures.
- Retain source values alongside transformations for revision tracking.

## Required procedure

1. Retrieve authoritative definitions and metadata.
2. Normalize defensible units and frequencies.
3. Compare relevant horizons and separate description from causal interpretation.

## Constraints (set by: operator)

Do not silently fill missing observations or present forecasts as actuals. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
