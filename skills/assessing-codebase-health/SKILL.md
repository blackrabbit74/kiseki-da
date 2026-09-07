---
name: assessing-codebase-health
description: "Assess code quality and technical debt using the project\u2019s actual checkers and comparable evidence. Use when the user requests a code-health review, quality baseline, or debt prioritization; not for an unrelated whole-repository rewrite or an unsupported universal quality score."
---

# Assessing Codebase Health

## Purpose

Assess code quality and technical debt using the project’s actual checkers and comparable evidence.

## Deliverable

Return check results, coverage gaps, representative findings, and prioritized remediation with evidence.

Done when: each check is marked passed, failed, or unavailable and recommendations reflect actual impact.

Stop and report when: a required checker cannot run because its environment is missing; identify the blocked action and continue independent work.

## Inputs

Project scripts, configuration, prior baseline, changed scope, and available tools.

## Decision rules

- Discover commands from project configuration rather than assuming tools from file extensions.
- Preserve original process exit status; output truncation or a pipe can hide a failure.
- An unavailable check is missing evidence, not a pass or automatic quality penalty.
- Compare trends only when tool versions, scope, and measurement rules are compatible.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Run relevant checkers with captured status and duration, inspect representative failures, and rank debt by user impact and change risk.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
