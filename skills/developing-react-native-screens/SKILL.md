---
name: developing-react-native-screens
description: "Implement and verify React Native or Expo screens using mobile navigation, lifecycle, and platform capabilities. Use when mobile screens, deep links, native APIs, or list behavior need changes; not for assuming browser DOM behavior or forcing managed Expo on a bare project."
---

# Developing React Native Screens

## Purpose

Implement and verify React Native or Expo screens using mobile navigation, lifecycle, and platform capabilities.

## Deliverable

Return the mobile change with target-platform evidence and any simulator or device limitations.

Done when: navigation, permissions, background transitions, and relevant rendering behavior match the contract.

Stop and report when: the required native module or target device runtime is unavailable; identify the blocked action and continue independent work.

## Inputs

React Native/Expo versions, workflow type, native modules, navigation, platform targets.

## Decision rules

- Deep-link parameters are untrusted input even when normal in-app navigation produces valid values.
- Foreground/background transitions can change network and subscription behavior.
- Large lists require stable identity and bounded rendering; web scrolling assumptions do not transfer automatically.
- Token storage requirements differ from ordinary persisted UI state.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Discover actual native capabilities, implement within current routing and state conventions, then test invalid links, denied permissions, list updates, and lifecycle transitions.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
