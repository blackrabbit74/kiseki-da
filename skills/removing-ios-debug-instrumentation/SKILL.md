---
name: removing-ios-debug-instrumentation
description: "Remove identified temporary iOS debug instrumentation while preserving application behavior and other test infrastructure. Use when the user asks to strip an installed debug bridge or generated QA wiring; not for general iOS cleanup or deleting all DEBUG blocks."
---

# Removing Ios Debug Instrumentation

## Purpose

Remove identified temporary iOS debug instrumentation while preserving application behavior and other test infrastructure.

## Deliverable

Return a targeted removal diff, affected dependency references, and debug/release verification evidence.

Done when: the identified instrumentation is absent from relevant sources and release artifacts without breaking the app.

Stop and report when: a candidate generated file contains user code whose ownership cannot be separated; identify the blocked action and continue independent work.

## Inputs

iOS project, instrumentation identifiers, package references, generated markers, target scheme.

## Decision rules

- Discover the actual package and generated-file provenance before removing anything.
- DEBUG blocks can contain unrelated diagnostics; remove only the requested instrumentation.
- An unused import search does not prove a binary excludes linked instrumentation.
- A disconnected device blocks device-token cleanup only, not source cleanup.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Inventory references and generated markers, remove the bounded wiring, then use available Xcode or Swift tooling to build relevant configurations and inspect artifacts where supported.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
