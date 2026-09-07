---
name: implementing-backend-boundaries
description: "Implement backend behaviors with explicit validation, business rules, and persistence boundaries. Use when a new API behavior spans layers or backend responsibilities are tangled; not for imposing a new architecture on unrelated code."
---

# Implementing Backend Boundaries

## Purpose

Implement backend behaviors with explicit validation, business rules, and persistence boundaries.

## Deliverable

Deliver the requested service change, contract examples, and relevant integration evidence.

Done when: valid, invalid, unauthorized, and persistence-failure paths match the intended contract.

Stop and report when: the ownership of a destructive data operation is unresolved; identify the blocked action and continue independent work.

## Inputs

Routes, middleware order, service conventions, schema, authentication model, supported dependencies.

## Decision rules

- Reuse existing boundaries; trivial queries do not require repository abstractions.
- Validate at entry but enforce business invariants where alternate callers cannot bypass them.
- Align transactions with business atomicity rather than each repository call.
- Middleware ordering affects authentication and error handling; inspect actual execution order.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Trace a nearby request end to end, implement the smallest complete behavior, and exercise HTTP errors and transaction rollback.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
