---
name: releasing-software
description: "Prepares and performs authorized software releases or deployments with artifact identity, rollout evidence, and recovery decisions. Use for shipping or launch preparation; not for assuming a successful upload proves the service works or publishing beyond the user\u2019s requested environment."
---

# Releasing Software

## Purpose

Release a known artifact with observable behavior and a feasible recovery path.

## Deliverable

Return release artifacts or deployment result, verification, monitoring criteria, and recovery limits.

Done when: the authorized release state and important user flows are verified.

Stop and report when: missing credentials, required checks, or authorization prevent a release step. Continue independent work and identify the blocked action.

## Inputs

Release scope, artifact revision, environment, checks, baseline metrics, and recovery method.

## Decision rules

- Separate deployed code from enabled features when flags are used.
- Choose rollout stages and hold or recovery thresholds from service risk and actual baselines.
- Check database compatibility before claiming an application rollback restores the whole system.

## Required procedure

1. Verify artifact identity and required preparation.
2. Prepare recovery and observability, then perform authorized rollout.
3. Inspect critical flows and metrics before advancing; report actual release state.

## Constraints (set by: operator)

Do not invent universal rollout percentages or send announcements without explicit permission. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
