---
name: designing-regression-tests
description: "Designs and implements behavior-focused tests that expose failures and protect meaningful contracts, using red-green-refactor when appropriate. Use for regression prevention, test strategy, or requested TDD; not for blanket coverage expansion or deleting working code because tests were written later."
---

# Designing Regression Tests

## Purpose

Create tests that fail for the intended defect and survive implementation changes.

## Deliverable

Return focused tests, demonstrated failure sensitivity, and relevant passing checks.

Done when: tests distinguish incorrect from intended behavior at a useful seam.

Stop and report when: an unavailable dependency prevents running a specific test. Continue independent work and identify the blocked action.

## Inputs

Behavior contract, defect reproduction, test framework, risk, and existing tests.

## Decision rules

- Choose unit, integration, or end-to-end scope by the failure boundary.
- Verify the test fails for the intended reason, not setup errors.
- Prefer observable behavior over private implementation details; avoid excessive mocks.

## Required procedure

1. Identify a high-value scenario and expected outcome.
2. Write a focused test and demonstrate failure sensitivity.
3. Implement or verify the repair, then refactor with relevant checks.

## Constraints (set by: operator)

Do not weaken assertions, erase implementation, or impose tests for trivial reversible edits. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
