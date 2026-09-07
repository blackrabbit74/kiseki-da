---
name: establishing-project-standards
description: "Defines or updates project-specific development rules and quality expectations from existing practice and explicit decisions. Use for team conventions or agent work standards; not for imposing arbitrary numeric gates or rewriting repository policy during routine implementation."
---

# Establishing Project Standards

## Purpose

Make the project’s actual quality expectations usable and checkable.

## Deliverable

Return concise rules with rationale, scope, verification, and unresolved ownership.

Done when: binding decisions are separated from proposals and each enforced rule has a realistic check.

Stop and report when: a required policy decision belongs to an unavailable owner. Continue independent work and identify the blocked action.

## Inputs

Existing standards, stack, CI, pain points, current measurements, and stakeholder decisions.

## Decision rules

- Read current conventions and enforcement before asking for preferences.
- Distinguish warning, blocking check, and advisory guidance.
- Baseline measurements inform thresholds; inherited example numbers are not commitments.

## Required procedure

1. Inventory current rules and observed failure patterns.
2. Draft the minimum rules that change decisions and identify authority.
3. Check consistency with existing automation and show how exceptions are handled.

## Constraints (set by: operator)

Do not silently weaken checks or install policy enforcement beyond the requested scope. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
