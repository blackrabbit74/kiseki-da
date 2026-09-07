---
name: selecting-software-dependencies
description: "Compares existing repository solutions, packages, and services against concrete functional and maintenance requirements. Use before adopting or building a substantial dependency; not for installing packages automatically from popularity rankings or researching every trivial helper."
---

# Selecting Software Dependencies

## Purpose

Choose the smallest sustainable solution that meets the real need.

## Deliverable

Return candidates, evidence, tradeoffs, recommendation, and a targeted validation result where feasible.

Done when: the recommendation accounts for fit, compatibility, maintenance, license, and integration cost.

Stop and report when: a missing private package or critical compatibility fact prevents a final selection. Continue independent work and identify the blocked action.

## Inputs

Required behavior, stack, constraints, existing dependencies, and evaluation criteria.

## Decision rules

- Search the repository before external catalogs.
- Distinguish adopt, extend, compose, and build by total maintenance cost rather than code volume.
- Verify current package identity, supported versions, and license from authoritative sources.

## Required procedure

1. Define must-have behavior and disqualifying constraints.
2. Inspect credible candidates and existing solutions.
3. Test the riskiest integration assumption and explain conditions that would change the choice.

## Constraints (set by: operator)

Do not invent maintenance status or install a new dependency solely because research found it. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
