---
name: developing-cpp-components
description: "Implement and verify C++ changes with explicit lifetime, ownership, and build-configuration reasoning. Use when a C++ component or test failure needs correction; not for non-C++ work or adding an unrelated testing framework."
---

# Developing Cpp Components

## Purpose

Implement and verify C++ changes with explicit lifetime, ownership, and build-configuration reasoning.

## Deliverable

Return the scoped change with compiler/build details and relevant regression or sanitizer evidence.

Done when: the affected behavior passes and lifetime or undefined-behavior risks have targeted checks.

Stop and report when: the required compiler or target environment is unavailable; identify the blocked action and continue independent work.

## Inputs

C++ standard, compiler, build presets, ownership contracts, failing cases.

## Decision rules

- Prefer RAII for ownership; distinguish owning pointers from borrowed views whose backing storage may expire.
- Container mutation can invalidate iterators and references even when a test happens to pass.
- Sanitizers detect exercised failures, not absence of undefined behavior; choose address, undefined, or race checks to match the risk.
- Keep test discovery compatible with cross-compilation instead of assuming target binaries run on the host.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Reproduce the behavior in the actual build configuration, change the smallest boundary, and run focused tests plus appropriate diagnostics.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
