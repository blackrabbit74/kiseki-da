---
name: developing-go-services
description: "Implement and verify Go packages and services with clear ownership, cancellation, and error semantics. Use when a Go feature, concurrency defect, or package boundary needs changes; not for adding abstractions or dependency frameworks without a concrete need."
---

# Developing Go Services

## Purpose

Implement and verify Go packages and services with clear ownership, cancellation, and error semantics.

## Deliverable

Return the scoped Go change with focused tests and relevant race or cancellation evidence.

Done when: failure and cancellation paths release resources and concurrent behavior satisfies the contract.

Stop and report when: the required Go toolchain or external test dependency is unavailable; identify the blocked action and continue independent work.

## Inputs

Module version, package interfaces, goroutine ownership, context deadlines, failing behavior.

## Decision rules

- Preserve wrapped causes for errors.Is and errors.As instead of inspecting strings.
- A typed nil inside an interface is not necessarily a nil interface.
- Specify who closes channels and how every goroutine exits; cancellation must reach blocking operations.
- A useful zero value cannot excuse writing to an uninitialized map or copying a used mutex.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Trace ownership and error propagation, implement the smallest package change, and exercise boundary cases, cancellation, and race detection where concurrency changed.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
