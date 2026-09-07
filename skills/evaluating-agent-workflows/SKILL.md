---
name: evaluating-agent-workflows
description: "Design and run bounded evaluations of agent or harness behavior against observable task outcomes. Use for reliability benchmarks, capability tests, or regression comparisons; passing a textual pattern check alone does not establish successful real task execution."
---

# Evaluating Agent Workflows

## Purpose

Design and run bounded evaluations of agent or harness behavior against observable task outcomes.

## Deliverable

Return the evaluation cases, environment and build identifiers, graders, raw outcome references, aggregate results, and unmeasured limitations.

Done when: results can be traced to actual runs and the rubric distinguishes capability improvements from regressions.

Stop and report when: the runner or required environment is unavailable; deliver the runnable protocol and mark execution unverified. Continue independent work and identify the specific blocked action.

## Inputs

Target workflow, baseline and candidate versions, realistic task fixtures, success criteria, cost limits, and accessible evaluation runner.

## Decision rules

- Use deterministic graders for observable invariants and calibrated judgment for open-ended quality.
- Specify criteria before inspecting candidate outputs; preserve holdout cases.
- Repeated attempts answer a different question from one-shot reliability; report attempt counts and aggregation explicitly.

## Required procedure

1. Define representative success and failure cases with fixed conditions.
2. Run available bounded trials while preserving artifacts and failure traces.
3. Compare outcomes, cost, and variability; identify grader blind spots and concrete regressions.

## Constraints (set by: operator)

Do not execute destructive or externally mutating evaluation cases without authorization, or change graders merely to make results pass. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
