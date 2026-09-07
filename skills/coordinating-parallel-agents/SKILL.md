---
name: coordinating-parallel-agents
description: "Coordinates explicitly authorized agent delegation across independent tasks with ownership, interface contracts, and integration checks. Use when parallel agent work is requested or authorized; not for tightly coupled tasks where agents would edit shared state without coordination."
---

# Coordinating Parallel Agents

## Purpose

Gain useful concurrency without conflicting ownership.

## Deliverable

Return integrated results, responsibility mapping, verification, and unresolved cross-task issues.

Done when: assigned outputs are reconciled and the combined result meets the parent objective.

Stop and report when: agent capacity or shared-state conflict prevents a delegation; continue work locally where possible. Continue independent work and identify the blocked action.

## Inputs

Objective, independent task boundaries, available agents, shared files, and acceptance conditions.

## Decision rules

- Parallelize only when tasks can progress without waiting on each other.
- Assign file or module ownership and tell workers not to revert others.
- Give sufficient relevant context; use minimal context only when independence benefits from it.

## Required procedure

1. Identify dependency edges and define bounded assignments.
2. Dispatch authorized work while doing useful independent work locally.
3. Collect evidence, resolve interface mismatches, and check integrated behavior.

## Constraints (set by: operator)

Delegation does not expand permissions or absolve the coordinator from integration. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
