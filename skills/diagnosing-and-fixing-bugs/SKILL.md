---
name: diagnosing-and-fixing-bugs
description: "Reproduces technical failures, tests competing causes, and implements a verified repair using evidence from the affected path. Use for bugs, failing tests, or unexpected behavior; not for speculative rewrites or withholding urgent mitigation until every cause is known."
---

# Diagnosing And Fixing Bugs

## Purpose

Repair the failure and explain the mechanism supported by evidence.

## Deliverable

Return reproduction, diagnosis, fix, and regression evidence.

Done when: the original symptom is checked after the repair and relevant neighboring behavior remains intact.

Stop and report when: missing environment or evidence prevents a specific diagnostic test. Continue independent work and identify the blocked action.

## Inputs

Failure details, logs, environment, recent changes, repository, and reproduction steps.

## Decision rules

- Trace inputs and outputs across boundaries to locate the first divergence.
- Change one hypothesis-bearing factor at a time where practical.
- Distinguish temporary mitigation from causal repair; urgent mitigation can proceed within scope.

## Required procedure

1. Reproduce or collect enough evidence to bound the failure.
2. Compare a working case and test plausible causes.
3. Implement the targeted repair and validate the original failure path.

## Constraints (set by: operator)

Do not disguise unrelated test failures or weaken checks to report success. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
