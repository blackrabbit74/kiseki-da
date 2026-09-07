---
name: developing-java-components
description: "Implement and verify Java components using the project\u2019s language level and actual framework conventions. Use when Java domain logic, collections, exceptions, or component boundaries need changes; not for automatically imposing Spring or Quarkus on a plain Java project."
---

# Developing Java Components

## Purpose

Implement and verify Java components using the project’s language level and actual framework conventions.

## Deliverable

Return the requested Java change with compiler and behavioral verification.

Done when: the affected contract and relevant resource, equality, and failure cases pass.

Stop and report when: the required JDK or build environment is unavailable; identify the blocked action and continue independent work.

## Inputs

Build files, JDK target, framework if present, API contracts, existing tests.

## Decision rules

- Records provide shallow immutability; mutable components may still need defensive copies.
- Keep equals and hashCode consistent when objects become map keys or set members.
- Avoid side effects in stream pipelines when ordering or parallel execution changes their meaning.
- Distinguish framework-managed transactions from ordinary method calls instead of inferring behavior from annotations alone.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Determine language and framework support, implement the bounded change, then test mutable aliases, resource closure, and exception behavior that affect the contract.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
