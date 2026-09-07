---
name: developing-react-interactions
description: "Implement and verify React components and hooks with clear state ownership and rendering boundaries. Use when React interaction, asynchronous data, or component lifecycle behavior needs changes; not for automatically adding global stores or memoization to unrelated code."
---

# Developing React Interactions

## Purpose

Implement and verify React components and hooks with clear state ownership and rendering boundaries.

## Deliverable

Return the requested component change with user-visible interaction and relevant rendering checks.

Done when: loading, error, repeated interaction, and cleanup behavior match the contract.

Stop and report when: the target rendering environment is unavailable for a required integration check; identify the blocked action and continue independent work.

## Inputs

React/framework versions, component tree, state sources, server/client boundary, interaction examples.

## Decision rules

- Derive values during render when possible; copying derived state into effects creates synchronization obligations.
- Effects synchronize external systems and must tolerate setup/cleanup repetition.
- Stable keys represent identity; array indices can attach state to the wrong item after reordering.
- Server/client boundaries affect serializable props, secret access, and where effects execute.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Trace the state owner, implement the interaction, then test user actions, stale async responses, reordered items, and teardown without relying only on snapshots.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
