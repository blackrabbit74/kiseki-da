---
name: improving-interface-appearance
description: "Evaluates and improves rendered interfaces for visual hierarchy, typography, spacing, and consistency with evidence from actual screens. Use for visual QA or design polish; not for a full product redesign or automatically replacing an established design system."
---

# Improving Interface Appearance

## Purpose

Make the interface easier to understand through coherent visual choices.

## Deliverable

Return prioritized visual findings and requested fixes with comparable evidence.

Done when: important issues are tied to observed screens and changes are checked at relevant sizes.

Stop and report when: inaccessible screens prevent judging a specific state. Continue independent work and identify the blocked action.

## Inputs

Screens or running interface, design references, user flow, scope, and code access.

## Decision rules

- Infer rendered conventions before proposing changes; distinguish intended variation from inconsistency.
- Prioritize orientation and action hierarchy above decorative polish.
- Compare before and after at identical viewport and state.

## Required procedure

1. Inspect representative screens and extract typography, color, and spacing patterns.
2. Identify issues by user impact and implement authorized corrections.
3. Recheck responsive layouts, overflow, and interaction states.

## Constraints (set by: operator)

Do not turn numeric style heuristics into universal rules or save design policy without scope. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
