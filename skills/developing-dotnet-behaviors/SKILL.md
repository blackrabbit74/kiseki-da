---
name: developing-dotnet-behaviors
description: "Implement and verify C# and .NET behavior with attention to asynchronous execution and dependency lifetimes. Use when changing a .NET service, API, or its tests; not for unrelated framework migration or mandatory replacement of the test stack."
---

# Developing Dotnet Behaviors

## Purpose

Implement and verify C# and .NET behavior with attention to asynchronous execution and dependency lifetimes.

## Deliverable

Return code changes with targeted tests and real boundary evidence where integration matters.

Done when: success, failure, cancellation, and disposal behavior match the contract.

Stop and report when: the target SDK or required integration service is unavailable; identify the blocked action and continue independent work.

## Inputs

Target framework, SDK, project references, DI registrations, test conventions.

## Decision rules

- Await asynchronous work and return Task in tests; async void can hide failures.
- Avoid capturing scoped dependencies in singleton services.
- A mocked repository cannot prove query translation or transaction behavior; use an appropriate real provider for those claims.
- Decimal arithmetic may suit monetary quantities, but rounding and currency units still need explicit contracts.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Trace dependency lifetimes and async boundaries, implement the change, then test cancellation and integration behavior with the existing test framework.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
