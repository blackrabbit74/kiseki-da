---
name: defining-operation-boundaries
description: "Defines or reviews practical permission boundaries for a specific automated workflow, including allowed writes, consequential actions, and recovery. Use when setting agent operating scope or reviewing a risky procedure; not for claiming a prose skill enforces sandbox restrictions."
---

# Defining Operation Boundaries

## Purpose

Make permitted operations and their enforcement explicit.

## Deliverable

Return a scoped operation map, required controls, and concrete blocked-action handling.

Done when: each consequential action has a known authorization source and actual enforcement is distinguished from guidance.

Stop and report when: a specific action lacks required authorization or a guard rejects it. Continue independent work and identify the blocked action.

## Inputs

Workflow, assets, directories, current permissions, user authorization, and available controls.

## Decision rules

- Judge the resolved target and effect, not command keywords alone.
- Separate reversible preparation from external mutation and destructive changes.
- Honor existing authorization; require new input only for an actually unapproved action.

## Required procedure

1. Inventory reads, writes, external effects, and recovery options.
2. Map each operation to existing authorization and technical boundaries.
3. Prepare permitted work and identify exact gaps in enforcement or authority.

## Constraints (set by: operator)

Do not disable or bypass guards, invent enforcement, or convert every action into a confirmation loop. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
