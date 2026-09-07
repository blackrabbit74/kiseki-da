---
name: implementing-interface-motion
description: "Implements UI animation and transitions that communicate state, guide attention, or preserve spatial continuity while respecting motion preferences. Use for interactive motion work; not for standalone video production or adding animation that delays essential interaction."
---

# Implementing Interface Motion

## Purpose

Make changes of state understandable without sacrificing responsiveness.

## Deliverable

Return implemented transitions and checks for interruption, reduced motion, and performance.

Done when: transitions work during rapid state changes and remain usable with motion reduced.

Stop and report when: an unavailable runtime prevents verifying a transition; provide implementation and test instructions. Continue independent work and identify the blocked action.

## Inputs

UI states, framework, existing animation library, design intent, and device constraints.

## Decision rules

- Use the installed animation system consistently instead of mixing incompatible contexts.
- Prefer transform and opacity where they fit; measure layout-heavy effects.
- Reduced motion must preserve state information, focus, and completion feedback.

## Required procedure

1. Map start, intermediate, interrupted, and final states.
2. Implement motion with the existing framework and current API guidance.
3. Test repeated toggles, navigation, reduced motion, and slower devices.

## Constraints (set by: operator)

Do not change libraries merely to follow a preferred stack. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
