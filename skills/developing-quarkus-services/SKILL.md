---
name: developing-quarkus-services
description: "Implement and verify Quarkus services with explicit CDI, reactive execution, and packaged-runtime behavior. Use when Quarkus endpoints, event handlers, or persistence flows need changes; not for mandatory Camel adoption or treating generic Java tests as runtime proof."
---

# Developing Quarkus Services

## Purpose

Implement and verify Quarkus services with explicit CDI, reactive execution, and packaged-runtime behavior.

## Deliverable

Return the service change with targeted tests and relevant Quarkus startup or packaged execution evidence.

Done when: dependency wiring, failure paths, and affected runtime behavior are verified.

Stop and report when: the required Quarkus toolchain or native target is unavailable; identify the blocked action and continue independent work.

## Inputs

Quarkus platform version, extensions, CDI scopes, messaging semantics, JVM/native target.

## Decision rules

- Blocking calls on event-loop threads can stall unrelated requests; inspect execution context.
- A mocked event publisher does not prove commit-to-publication consistency or redelivery behavior.
- Build-time configuration and runtime configuration have different change boundaries.
- JVM tests cannot prove native-image reflection or resource inclusion.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Identify the relevant runtime boundary, implement the feature, and test CDI wiring, event failure/redelivery, and packaged startup where affected.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
