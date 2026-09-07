---
name: auditing-agent-configuration
description: "Audit a user-selected agent configuration for broken references, redundant entries, and reclaimable generated state. Use when the user requests configuration cleanup, repair, or startup-noise diagnosis; not for unrelated project refactoring or weakening permission controls for convenience."
---

# Auditing Agent Configuration

## Purpose

Audit a user-selected agent configuration for broken references, redundant entries, and reclaimable generated state.

## Deliverable

Return evidence-ranked findings and authorized reversible repairs with precise recovery information.

Done when: changed references resolve and affected runtime behavior is checked or explicitly untested.

Stop and report when: ownership or active use of a proposed cleanup target cannot be established; identify the blocked action and continue independent work.

## Inputs

Named runtime, selected configuration paths, startup evidence, installed components, cleanup scope.

## Decision rules

- Discover the actual runtime and configuration schema; do not assume another harness’s home directory.
- Old modification time alone does not establish obsolescence.
- Check incoming references and dynamic discovery before labeling files orphaned.
- Permission simplification can change authority even when strings appear redundant; keep that separate from cache cleanup.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Inventory only selected channels, verify candidates against their consumers, apply scoped reversible fixes, and inspect actual runtime health without deleting active state.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
