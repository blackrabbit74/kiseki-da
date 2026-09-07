---
name: routing-task-workflows
description: "Identify which available skill or direct workflow best fits a concrete task and its current stage. Use when skill choice or the next work path is unclear; this is not a mandatory startup ritual or permission to impose a complete development lifecycle."
---

# Routing Task Workflows

## Purpose

Identify which available skill or direct workflow best fits a concrete task and its current stage.

## Deliverable

Return the chosen route, brief fit rationale, relevant prerequisites, and the next useful action.

Done when: selection follows the requested outcome and available capabilities without expanding the user’s task.

Stop and report when: two routes require materially different outcomes that cannot be inferred; clarify only that choice while preparing common work. Continue independent work and identify the specific blocked action.

## Inputs

User intent, current artifacts, unresolved decision, available skill descriptions, and actual tool capabilities.

## Decision rules

- Select by deliverable and current uncertainty, not keyword overlap alone.
- Prefer direct work when no skill contributes useful decisions.
- Load only the chosen skill and required references; do not recursively invoke an entire catalog.

## Required procedure

1. Identify the next result needed and whether the issue is scope, implementation, evidence, or operation.
2. Compare plausible available routes and inspect the best match.
3. Explain the choice briefly and proceed with authorized work, retaining existing constraints.

## Constraints (set by: operator)

Do not invent unavailable skills or elevate a routing guide above the user’s explicit product and process choices. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
