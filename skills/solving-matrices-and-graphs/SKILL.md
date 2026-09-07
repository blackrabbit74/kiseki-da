---
name: solving-matrices-and-graphs
description: "Analyze linear systems or graph rankings with explicit numerical assumptions, error measures, and computational limits. Use when matrix conditioning, solver choice, or PageRank computation needs practical analysis; not for unverified sublinear speed claims or inferring real-world influence from ranking alone."
---

# Solving Matrices And Graphs

## Purpose

Analyze linear systems or graph rankings with explicit numerical assumptions, error measures, and computational limits.

## Deliverable

Return results with data representation, method, convergence evidence, residuals, and interpretation limits.

Done when: numerical error and graph normalization checks support the reported result.

Stop and report when: available numerical tools cannot handle the required size within the stated resource bound; identify the blocked action and continue independent work.

## Inputs

Matrix or graph data, dimensions, sparsity, edge meaning, tolerance, resource budget.

## Decision rules

- Regularization changes the problem; disclose its effect instead of silently forcing solver assumptions.
- A small residual does not guarantee small solution error for an ill-conditioned system.
- PageRank requires explicit edge direction, dangling-node treatment, and personalization normalization.
- Sorting scores must preserve node identifiers; array position is not evidence of influence.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Discover actual numerical libraries or solver capabilities, inspect input properties, select a suitable method, and validate against a small reference case plus residual and convergence checks.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
