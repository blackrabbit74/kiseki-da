---
name: testing-interactive-applications
description: "Tests browser or app user flows and produces reproducible findings with observed states and coverage. Use for functional QA, exploratory testing, or regression checks; not for claiming exhaustive coverage from screenshots or changing code when the user requested report-only testing."
---

# Testing Interactive Applications

## Purpose

Determine whether real user tasks work in the tested environment.

## Deliverable

Return test coverage, reproducible issues, expected versus actual behavior, and evidence.

Done when: important flows and relevant failure states are exercised and findings are reproducible.

Stop and report when: authentication or unavailable environment blocks a particular flow. Continue independent work and identify the blocked action.

## Inputs

App access, target flows, environment, test accounts, and report or fix scope.

## Decision rules

- Prioritize core tasks over incidental pages.
- Inspect empty, loading, invalid-input, error, and navigation states.
- Use test data and authorized effects; production checkout testing does not imply purchase permission.

## Required procedure

1. Map reachable controls and define task-based coverage.
2. Exercise flows and record evidence at the point of failure.
3. Repeat suspected failures and report exact reproduction plus untested areas.

## Constraints (set by: operator)

Preserve report-only scope and never expose credentials in evidence. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
