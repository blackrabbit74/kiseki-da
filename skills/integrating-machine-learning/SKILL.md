---
name: integrating-machine-learning
description: "Add a measurable machine-learning capability to existing software with a reproducible baseline and controlled inference boundary. Use for classification, ranking, recommendation, or forecasting integration; a request to add ML does not justify replacing working rules without evidence."
---

# Integrating Machine Learning

## Purpose

Add a measurable machine-learning capability to existing software with a reproducible baseline and controlled inference boundary.

## Deliverable

Return the data and inference contracts, baseline comparison, reproducible model artifact or training path, fallback behavior, and integration checks.

Done when: the model is evaluated on suitable held-out data and failure handling preserves the application’s required behavior.

Stop and report when: data quality, labels, or permitted compute cannot support training; deliver the baseline and integration design with the missing prerequisite. Continue independent work and identify the specific blocked action.

## Inputs

Business decision and error costs, existing heuristics, data provenance, labels, latency constraints, deployment environment, and evaluation budget.

## Decision rules

- Compare against a meaningful heuristic baseline before adding complexity.
- Split by time or entity where leakage would invalidate random splits.
- Separate preprocessing and inference from business logic; specify missing-feature and timeout behavior.
- Use fallback or abstention that is appropriate to the application’s mistake cost.

## Required procedure

1. Define success metrics and audit data readiness and leakage.
2. Implement reproducible preprocessing and a simple model with verified current library interfaces.
3. Evaluate against the baseline, integrate behind a reversible boundary, and test inference schemas and failure cases.

## Constraints (set by: operator)

Do not claim model improvement from training accuracy or deploy and retrain on live user data beyond the authorized scope. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
