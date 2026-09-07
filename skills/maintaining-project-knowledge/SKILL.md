---
name: maintaining-project-knowledge
description: "Repair drift in project knowledge by clarifying canonical sources for rules, structure, status, and decision history. Use for long-lived documentation that contradicts implementation or repeatedly loses context; a one-time repository tour does not require documentation governance."
---

# Maintaining Project Knowledge

## Purpose

Repair drift in project knowledge by clarifying canonical sources for rules, structure, status, and decision history.

## Deliverable

Return a source-role map, corrected documentation, links to canonical facts, and remaining authority conflicts.

Done when: important facts have an identifiable owner and current status does not overwrite historical reasoning.

Stop and report when: contradictory authoritative decisions cannot be resolved from available evidence; preserve the variants while repairing independent drift. Continue independent work and identify the specific blocked action.

## Inputs

Existing documentation, code and configuration, decision records, status sources, ownership conventions, and requested changes.

## Decision rules

- Reuse existing documents; roles do not require separate files.
- Link to a canonical fact rather than copying it into multiple summaries.
- Preserve intentional removals and their rationale so obsolete approaches are not recreated.

## Required procedure

1. Inventory relevant sources and map rules, structure, status, and history.
2. Check disputed facts against actual artifacts and recorded decisions.
3. Update the smallest relevant sections and verify navigation and remaining conflicts.

## Constraints (set by: operator)

Do not claim automatic agent loading unless a real mechanism exists; instruction or hook changes require their own authorized scope. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
