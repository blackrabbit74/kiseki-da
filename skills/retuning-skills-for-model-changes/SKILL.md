---
name: retuning-skills-for-model-changes
description: "Adjust a skill corpus for a changed model using comparable behavioral evidence and a predefined improvement bar. Use when a model change causes workflow regressions; shortening prose or passing static checks alone does not demonstrate successful retuning."
---

# Retuning Skills For Model Changes

## Purpose

Adjust a skill corpus for a changed model using comparable behavioral evidence and a predefined improvement bar.

## Deliverable

Return baseline and candidate identities, measured changes, retained regressions, noise estimates, and a revised corpus or specific unsupported claims.

Done when: the predefined behavioral bar is met on the target model, with remaining coverage limits stated.

Stop and report when: there is no repeatable task or way to select comparable corpus builds; prepare the measurement setup without claiming retuning success. Continue independent work and identify the specific blocked action.

## Inputs

Target model, corpus, run archive, comparable build selector, task fixtures, traces, and evaluation budget.

## Decision rules

- Estimate run variability with equivalent builds before attributing changes to prose.
- Register success criteria before editing; choose fixes from observed failures.
- Distinguish legitimate user decisions from accidental stalling before removing stopping conditions.

## Required procedure

1. Inspect existing runs and establish a comparable baseline.
2. Make one attributable revision at a time and rerun relevant cases.
3. Keep changes supported by results and report regressions, cost, and behavior that was never exercised.

## Constraints (set by: operator)

Do not weaken tests to hide regressions or invent empirical differences between model families. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
