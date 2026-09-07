---
name: developing-laravel-features
description: "Implement and verify Laravel application behavior across requests, policies, Eloquent, and queued effects. Use when a Laravel endpoint, model workflow, or feature test needs changes; not for forcing Pest or PHPUnit migration or silently touching production data."
---

# Developing Laravel Features

## Purpose

Implement and verify Laravel application behavior across requests, policies, Eloquent, and queued effects.

## Deliverable

Return the requested change and relevant HTTP, database, and queue-boundary evidence.

Done when: validation, authorization, persistence, and failure behavior match the contract.

Stop and report when: test database identity cannot be verified before a reset or migration; identify the blocked action and continue independent work.

## Inputs

Laravel/PHP versions, routes, form requests, policies, model settings, test configuration.

## Decision rules

- Mass-assignment rules do not replace authorization; test who may change each resource.
- A fake queue proves dispatch intent, not worker execution or transaction timing.
- SQLite tests may miss production-engine constraints and SQL differences.
- Disabling exception handling globally can invalidate tests of normal HTTP error responses.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Trace the request and model changes, implement within existing conventions, then verify unauthorized input, database effects, and any commit-dependent job dispatch.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
