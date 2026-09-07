---
name: recovering-failed-agent-runs
description: "Diagnose repeated agent failures and recover from the last verified state with a contained corrective action. Use for retry loops, context drift, tool errors, or environment mismatches; ordinary application bug fixing and bypassing runtime restrictions are outside this workflow."
---

# Recovering Failed Agent Runs

## Purpose

Diagnose repeated agent failures and recover from the last verified state with a contained corrective action.

## Deliverable

Return failure evidence, likely cause and alternatives, recovery action, observed result, and a resumable checkpoint.

Done when: recovery produces verified progress or isolates a specific external blocker without repeating unchanged failed actions.

Stop and report when: a policy boundary or unavailable prerequisite blocks the next action, or a proposed retry risks duplicating an uncertain side effect. Continue independent work and identify the specific blocked action.

## Inputs

Intended objective, recent tool sequence, errors, last successful step, working directory and revision, and current resource limits.

## Decision rules

- Classify logic, environment, state, and policy failures before choosing recovery.
- After a timeout, inspect remote or filesystem state before replaying a mutation.
- Repeated identical failures require a changed hypothesis or prerequisite, not merely another attempt.

## Required procedure

1. Capture concise failure and current-state evidence.
2. Test the smallest distinguishing hypothesis, including path, port, revision, and quota assumptions.
3. Apply a bounded correction, verify progress, and record unresolved conditions for continuation.

## Constraints (set by: operator)

Do not disable guards or broaden permissions to make a failed action succeed; preserve existing work during recovery. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
