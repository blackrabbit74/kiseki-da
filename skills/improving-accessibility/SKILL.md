---
name: improving-accessibility
description: "Audits or implements accessible interface behavior for keyboard, assistive technology, focus, contrast, and reflow. Use when accessibility barriers or conformance requirements need concrete work; not for declaring full standards compliance from an automated scan alone."
---

# Improving Accessibility

## Purpose

Remove observed barriers to completing user tasks.

## Deliverable

Return evidence-backed findings or fixes with tested states and remaining coverage.

Done when: the relevant task works with applicable input and assistive modes, within tested coverage.

Stop and report when: missing platform access prevents a required assistive-technology check. Continue independent work and identify the blocked action.

## Inputs

Interface, platform, target standard, user flows, and available testing tools.

## Decision rules

- Prefer native semantics and correct name, role, and value before adding ARIA.
- Manage focus on opening, closing, and errors without trapping users.
- Verify current authoritative criteria and exceptions rather than assuming all targets share one threshold.

## Required procedure

1. Inspect semantics and keyboard order in relevant states.
2. Test zoom, contrast, alternatives, and announcements; implement scoped fixes.
3. Repeat manual task checks and relevant automated checks.

## Constraints (set by: operator)

Report scan coverage honestly; do not equate no detected errors with conformance. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
