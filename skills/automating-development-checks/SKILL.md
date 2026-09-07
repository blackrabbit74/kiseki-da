---
name: automating-development-checks
description: "Configure or repair automated build and quality checks using existing project commands and CI providers. Use for CI workflows, pre-commit checks, or failed pipeline feedback; it does not authorize deployments or unrelated repository protection changes."
---

# Automating Development Checks

## Purpose

Configure or repair automated build and quality checks using existing project commands and CI providers.

## Deliverable

Return workflow or hook changes, trigger coverage, required checks, validation results, and remaining environment dependencies.

Done when: configured checks run intended commands and failures propagate instead of producing false success.

Stop and report when: a required remote setting or secret cannot be accessed; leave its exact configuration requirement. Continue independent work and identify the specific blocked action.

## Inputs

Existing workflows, lockfiles, scripts, hooks, runner constraints, and relevant failure logs.

## Decision rules

- Reuse real checks rather than inventing scripts to fill a checklist.
- Separate pull-request execution from privileged release credentials.
- Cache keys must reflect lockfiles and toolchains; selective paths must account for shared dependencies.

## Required procedure

1. Map commands and trigger coverage, including hook conflicts.
2. Implement an integrated workflow and classify failures by job and step.
3. Validate syntax and representative checks; distinguish local validation from a real CI run.

## Constraints (set by: operator)

Do not mask failures by disabling checks or overwrite existing hooks without preserving their behavior. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
