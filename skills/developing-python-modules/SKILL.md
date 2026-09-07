---
name: developing-python-modules
description: "Implement and verify Python modules with clear contracts, resource management, and runtime-compatible typing. Use when Python behavior, package boundaries, or asynchronous execution need changes; not for format-only edits or mandatory dependency and architecture replacement."
---

# Developing Python Modules

## Purpose

Implement and verify Python modules with clear contracts, resource management, and runtime-compatible typing.

## Deliverable

Return the requested change with focused tests and relevant typing or runtime evidence.

Done when: normal and failure paths preserve the contract without resource or state leakage.

Stop and report when: the required interpreter or dependency environment is unavailable; identify the blocked action and continue independent work.

## Inputs

Python version, project metadata, input contracts, async boundaries, existing test conventions.

## Decision rules

- Type annotations do not validate external data at runtime.
- Mutable defaults and class-level mutable state can leak between calls or instances.
- Catch only the operation whose failure is expected; broad try blocks can disguise unrelated KeyError or TypeError bugs.
- Blocking work inside async functions still blocks the event loop; choose an appropriate execution boundary.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Trace inputs and side effects, implement the bounded change, and test repeated calls, resource cleanup, malformed data, and cancellation where applicable.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
