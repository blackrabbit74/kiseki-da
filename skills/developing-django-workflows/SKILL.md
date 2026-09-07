---
name: developing-django-workflows
description: "Implement and verify Django request, persistence, and background-job behavior with explicit transaction and delivery semantics. Use when a Django feature or Celery task needs development or repair; not for mandatory Celery installation or unrelated Python scripting."
---

# Developing Django Workflows

## Purpose

Implement and verify Django request, persistence, and background-job behavior with explicit transaction and delivery semantics.

## Deliverable

Return the scoped implementation and evidence from request, database, and worker boundaries that matter.

Done when: transaction rollback and repeated task delivery preserve intended state.

Stop and report when: broker or database access is unavailable for a required integration check; identify the blocked action and continue independent work.

## Inputs

Django settings, model constraints, job configuration, installed versions, target behavior.

## Decision rules

- Dispatch work after the relevant transaction commits; otherwise a worker can observe missing or rolled-back rows.
- Pass stable identifiers rather than model instances into tasks and recheck current state at execution.
- Late acknowledgement changes redelivery behavior; it does not make tasks exactly once.
- Eager task tests cannot prove broker routing, serialization, or worker crash recovery.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Trace request-to-commit-to-task order, implement idempotent effects, and test rollback, duplicate delivery, serialization, and permissions using the appropriate boundary.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
