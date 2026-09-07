---
name: analyzing-business-data
description: "Answers a business question from supplied structured data using reproducible calculations and explicit data-quality limits. Use for aggregations, joins, trends, cohort comparisons, or scenario calculations; financial or causal conclusions require evidence beyond a descriptive table."
---

# Analyzing Business Data

## Purpose

Produce a decision-relevant answer whose calculation and data boundaries can be reproduced.

## Deliverable

Return the answer, input and filter definitions, calculations or query, reconciled counts, important data-quality limits, and a chart only when useful.

Done when: the reported result is reproduced from the stated inputs, with row counts, join behavior, units, missing values, and denominators accounted for.

Stop and report when: data access, meaning, or quality makes the requested inference unreliable; report the specific missing input or limit.

## Inputs

Use the question, dataset, data dictionary, time zone and period, entity grain, and available computation tools.

## Decision rules

- If joining tables, check key uniqueness and compare pre-join and post-join row counts.
- If values are missing, distinguish missing, zero, not applicable, and excluded records.
- If data exceeds practical memory, aggregate near the source or process in chunks.
- If comparing periods or groups, align definitions and exposure before interpreting differences.

## Required procedure

1. Inspect schema, grain, size, types, duplicates, and relevant missingness.
2. Compute the requested result with an inspectable query or script.
3. Reconcile totals and denominators, then explain the conclusion and its limits.

## Constraints (set by: operator)

- Do not infer causation or forecast certainty from a descriptive pattern. Instead, report the association and evidence needed for stronger claims.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
