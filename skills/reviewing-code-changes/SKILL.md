---
name: reviewing-code-changes
description: "Reviews a specified code diff for correctness, requirement alignment, and documented project conventions, reporting actionable findings with evidence. Use for pull requests, branches, or pending changes; not for automatically rewriting code or presenting style preferences as defects."
---

# Reviewing Code Changes

## Purpose

Identify changes that matter to correctness and intended behavior.

## Deliverable

Return prioritized findings with locations, triggers, consequences, and relevant requirements.

Done when: findings are supported by inspected code and review coverage is explicit.

Stop and report when: an unresolved comparison target prevents identifying the review scope. Continue independent work and identify the blocked action.

## Inputs

Diff or comparison target, requirements, repository conventions, and test context.

## Decision rules

- Pin the intended comparison and distinguish merge-base review from direct revision comparison.
- Inspect callers and tests before asserting a defect.
- Separate documented violations from maintainability judgments; suppress unsupported speculation.

## Required procedure

1. Resolve the diff and locate the specification.
2. Trace changed behavior, failure paths, and consumers.
3. Report actionable findings and distinguish unreviewed or unavailable evidence.

## Constraints (set by: operator)

A review request does not authorize external comments or changes by itself. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
