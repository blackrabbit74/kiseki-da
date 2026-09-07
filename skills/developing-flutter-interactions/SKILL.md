---
name: developing-flutter-interactions
description: "Implement and verify Flutter and Dart interactions across state, widgets, navigation, and asynchronous work. Use when a Flutter feature or lifecycle defect needs code changes; not for switching state frameworks without a demonstrated need."
---

# Developing Flutter Interactions

## Purpose

Implement and verify Flutter and Dart interactions across state, widgets, navigation, and asynchronous work.

## Deliverable

Return the requested change with analyzer results and relevant widget or device checks.

Done when: loading, error, navigation, and disposal paths behave correctly.

Stop and report when: the target platform runtime is unavailable for a device-specific check; identify the blocked action and continue independent work.

## Inputs

Flutter/Dart versions, widget tree, state conventions, navigation, platform targets.

## Decision rules

- After await, a BuildContext may no longer be mounted; verify lifecycle before UI effects.
- Keep build methods free of repeated network or state-changing side effects.
- Do not replace absent business data with a valid-looking zero merely to satisfy null safety.
- Cancel or dispose subscriptions, controllers, and listeners at their owning lifecycle boundary.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Trace state ownership, implement the interaction, run analysis, and test unmount during async work, rebuilds, navigation guards, and platform behavior where relevant.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
