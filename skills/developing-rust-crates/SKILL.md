---
name: developing-rust-crates
description: "Implement and verify Rust crate behavior with explicit ownership, error, feature, and asynchronous contracts. Use when Rust functions, traits, concurrent code, or public API tests need changes; not for adding unsafe code or new mock frameworks without a concrete need."
---

# Developing Rust Crates

## Purpose

Implement and verify Rust crate behavior with explicit ownership, error, feature, and asynchronous contracts.

## Deliverable

Return the scoped Rust change with relevant unit, integration, documentation, or property evidence.

Done when: supported feature/target combinations and affected failure paths behave as intended.

Stop and report when: the required target toolchain or test runtime is unavailable; identify the blocked action and continue independent work.

## Inputs

Rust edition, MSRV if specified, Cargo features, public contracts, runtime choices.

## Decision rules

- Do not clone solely to silence ownership errors before understanding the intended lifetime.
- Avoid holding synchronization guards across await unless the primitive and protocol require it.
- Arithmetic overflow behavior can differ by build settings; encode checked or wrapping intent explicitly.
- A default-feature test does not establish no-default-features or alternate-target compatibility.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Identify ownership and API invariants, implement the change, and test boundary values, error variants, cancellation safety, and relevant feature combinations.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
