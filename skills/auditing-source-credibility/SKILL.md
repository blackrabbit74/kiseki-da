---
name: auditing-source-credibility
description: "Audits whether a supplied article, study, or report supports its claims by separating data quality, producer interests, and editorial distortion. Use when questioning credibility, bias, causal inflation, or a headline’s relationship to underlying evidence."
---

# Auditing Source Credibility

## Purpose

Locate how a claim changes between underlying evidence and its presentation.

## Deliverable

Return the claimed conclusion, underlying evidence, data limitations, disclosed interests, editorial additions, supported conclusion, and missing information.

Done when: each criticism points to a specific observation and distinguishes evidence weakness from speculation about motives.

Stop and report when: the primary source or methodological details are inaccessible; limit the audit and identify the inaccessible layer.

## Inputs

Use the supplied source, its cited studies or data, methodology, and public funding or conflict disclosures.

## Decision rules

- If the input is already a primary study, omit a journalism layer unless a secondary interpretation is also being assessed.
- If funding creates an incentive, report it separately from whether the method or result is invalid.
- If a headline changes population, metric, or causal strength, show the exact mismatch.
- If the abstract lacks methodological detail, narrow the assessment rather than filling the gap.

## Required procedure

1. Trace the headline or conclusion to the underlying evidence.
2. Examine sampling, measurement, comparator, and causal interpretation.
3. Separate producer incentives and editorial changes from what the data supports.

## Constraints (set by: operator)

- Do not declare a source false solely because its author has an interest. Instead, identify the evidential consequence of each concern.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
