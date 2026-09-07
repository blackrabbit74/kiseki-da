---
name: building-container-environments
description: "Build or repair container definitions and multi-service environments with explicit lifecycle and persistence behavior. Use when working on Dockerfiles, Compose services, or equivalent runtime setup; not for unrelated cloud migration or automatic production deployment."
---

# Building Container Environments

## Purpose

Build or repair container definitions and multi-service environments with explicit lifecycle and persistence behavior.

## Deliverable

Return configuration and observed build, readiness, networking, restart, and persistence checks.

Done when: services communicate correctly and restart behavior preserves specified data.

Stop and report when: runtime access is unavailable for starting containers; identify the blocked action and continue independent work.

## Inputs

Manifests, lockfiles, host architecture, ports, volume requirements, environment scope.

## Decision rules

- Development mounts may hide image contents; distinguish them from production artifacts.
- Startup ordering does not prove readiness; clients still need bounded connection recovery.
- Separate container DNS names from host endpoints and expose only required ports.
- Container tests do not establish native macOS or Windows compatibility.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Discover the actual runtime, build required targets, then check service discovery, health, restart, and teardown without deleting unrelated volumes.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
