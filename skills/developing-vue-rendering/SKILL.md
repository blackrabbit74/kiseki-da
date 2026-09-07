---
name: developing-vue-rendering
description: "Implement and verify Vue or Nuxt rendering, reactive state, and data-loading behavior. Use when a Vue feature or Nuxt hydration and route-data defect needs changes; not for disabling server rendering globally to hide mismatches."
---

# Developing Vue Rendering

## Purpose

Implement and verify Vue or Nuxt rendering, reactive state, and data-loading behavior.

## Deliverable

Return the scoped change with relevant component, SSR, hydration, and navigation evidence.

Done when: initial markup and client state agree and navigation refreshes the intended data.

Stop and report when: the SSR or target deployment runtime is unavailable for a required check; identify the blocked action and continue independent work.

## Inputs

Vue/Nuxt version, route behavior, state ownership, rendering mode, cache requirements.

## Decision rules

- Server and first client render must be deterministic; browser storage, random values, and current time need deliberate boundaries.
- Nuxt async-data keys define cache identity and must distinguish genuinely different data.
- Keep SSR data handlers free of mutations that may repeat during rendering or refresh.
- Shared server module state can leak data between requests; test isolation for user-specific values.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Identify reactive and server/client boundaries, implement the change, and test initial load, hydration, changed route parameters, and cross-request isolation.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
