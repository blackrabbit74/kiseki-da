---
name: developing-spring-boot-services
description: "Implement and verify Spring Boot service behavior across MVC, dependency injection, security, and transactions. Use when a Spring Boot feature, endpoint, or persistence defect needs changes; not for assuming plain Mockito tests prove Spring-managed behavior."
---

# Developing Spring Boot Services

## Purpose

Implement and verify Spring Boot service behavior across MVC, dependency injection, security, and transactions.

## Deliverable

Return code changes with the smallest suitable test slice and integration evidence for framework-managed behavior.

Done when: request, authorization, transaction, and failure cases match the intended contract.

Stop and report when: the required test context or database environment cannot start; identify the blocked action and continue independent work.

## Inputs

Boot version, dependencies, profiles, bean scopes, security configuration, transaction boundaries.

## Decision rules

- Self-invocation may bypass proxy-based advice; verify the actual transaction or async call path.
- A web slice does not automatically prove the full security and persistence configuration.
- Transactional tests can hide missing commit behavior; explicitly test commit-dependent effects.
- Use the active framework version’s testing APIs instead of copying deprecated annotations.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Trace request-to-service boundaries, implement the change, and exercise both permitted and denied requests plus rollback or commit behavior where relevant.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
