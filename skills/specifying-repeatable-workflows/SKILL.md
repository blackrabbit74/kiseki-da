---
name: specifying-repeatable-workflows
description: "Turn a recurring activity into an implementable workflow with triggers, inputs, outputs, and exception handling. Use for proceduralizing or preparing automation of routine work; not every workflow needs AI, a schedule, or a human checkpoint."
---

# Specifying Repeatable Workflows

## Purpose

Turn a recurring activity into an implementable workflow with triggers, inputs, outputs, and exception handling.

## Deliverable

Return a workflow specification and, when requested, an implementation with trigger semantics, state, outputs, exceptions, and verification.

Done when: an implementer can determine what happens on a normal run, duplicate trigger, missing input, and partial failure.

Stop and report when: an unresolved decision changes an external action or irreversible outcome; continue common preparation and document that branch. Continue independent work and identify the specific blocked action.

## Inputs

Observed routine, desired outcome, current tools, frequency or events, authority boundaries, and examples of exceptions.

## Decision rules

- Prefer event triggers when they match the actual work; schedules are not mandatory.
- Place any necessary human decision after useful preparation so it is concrete and reviewable.
- Model retries and duplicate events explicitly when actions create messages, records, or charges.

## Required procedure

1. Map a real occurrence and identify repeated decisions versus mechanical steps.
2. Specify trigger, state transitions, outputs, and recovery using existing tools.
3. Walk through normal and exceptional cases; implement and test only the requested automation scope.

## Constraints (set by: operator)

Do not create recurring jobs or send messages merely because a workflow spec mentions them. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
