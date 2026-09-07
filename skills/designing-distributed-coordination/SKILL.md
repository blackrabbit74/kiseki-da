---
name: designing-distributed-coordination
description: "Design coordination among distributed workers using workload and failure evidence. Use when implementing topology changes, shared task ownership, or adaptive routing; not for automatically spawning teams or assuming consensus from framework labels."
---

# Designing Distributed Coordination

## Purpose

Design coordination among distributed workers using workload and failure evidence.

## Deliverable

Return a protocol or scoped implementation with ownership, message semantics, adaptation criteria, and failure tests.

Done when: duplicate delivery, stale workers, and topology transitions preserve stated invariants.

Stop and report when: required consistency or failure assumptions cannot be established; identify the blocked action and continue independent work.

## Inputs

Worker model, communication pattern, failure budget, measured workload, existing code.

## Decision rules

- A faster topology is unsuitable if it loses ownership or ordering guarantees.
- Use hysteresis and an observation window to prevent adaptive switching oscillation.
- A missing heartbeat signals suspicion, not proof that work stopped.
- Reassignment may require epochs or fencing to reject stale workers.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Identify contention and failure domains, specify ownership transitions, and exercise delay, duplicate messages, worker loss, and recovery.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
