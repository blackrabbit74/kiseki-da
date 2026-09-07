---
name: running-bounded-work-loops
description: "Runs authorized iterative work with measurable progress, acceptance checks, checkpoints, and recovery decisions. Use for sustained improvement or repair loops; not for creating recurring automations without request or retrying unchanged failures indefinitely."
---

# Running Bounded Work Loops

## Purpose

Keep iterative execution directed toward a finite outcome.

## Deliverable

Return the completed result or checkpoint with progress evidence and exact remaining obstacle.

Done when: the acceptance condition is met and the loop stops.

Stop and report when: an explicit budget is exhausted; stop covered execution and checkpoint remaining work. If only a dependency lacks input or access, identify that blocked action and continue independent work while budget permits.

## Inputs

Goal, evaluation method, authorized scope, time or cost bounds, and current state.

## Decision rules

- Choose an observable improvement measure before repeating work.
- Repeated identical failure needs a changed hypothesis, smaller probe, or external input.
- Checkpoint completed work so retries do not recreate outputs or repeat side effects.

## Required procedure

1. Define the next bounded unit and its success evidence.
2. Execute, evaluate, and record progress.
3. Continue only while work changes relevant evidence; stop on completion or a genuine blocker.

## Constraints (set by: operator)

Do not claim background persistence without a configured supported mechanism. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
