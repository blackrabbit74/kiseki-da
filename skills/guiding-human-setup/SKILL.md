---
name: guiding-human-setup
description: "Prepare interactive guidance for setup steps requiring human account access or dashboard actions. Use when manual provisioning is a real dependency in the requested setup; not for delegating steps the agent can perform under existing authorization."
---

# Guiding Human Setup

## Purpose

Prepare interactive guidance for setup steps requiring human account access or dashboard actions.

## Deliverable

Return a verified sequence or requested wizard mapping manual actions to resulting values and destinations.

Done when: every stage has a known outcome and completed changes can be resumed without repetition.

Stop and report when: a current dashboard path or required account capability cannot be verified; identify the blocked action and continue independent work.

## Inputs

Configuration examples, consumed variables, target services, account state, manual-action boundaries.

## Decision rules

- Collect secrets through protected entry rather than echoing them into a transcript.
- Match variable names to actual consumers and collect no unused credentials.
- Make repeated writes idempotent and distinguish existing state from failed setup.
- Syntax checks alone do not verify the interactive journey.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Separate human-only steps, verify current UI or documentation, then statically check any wizard and label untested interactive stages.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
