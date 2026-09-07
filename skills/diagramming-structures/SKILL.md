---
name: diagramming-structures
description: "Turns a process, hierarchy, relationship network, or state model into an editable diagram with clear semantics. Use when a structural visualization clarifies a consulting argument, research model, or JRPG world and character relationships."
---

# Diagramming Structures

## Purpose

Make important relationships inspectable without inventing connections.

## Deliverable

Return editable diagram source, a rendered view when supported, a legend where needed, and any uncertain relationships or render limits.

Done when: nodes and edges match the supplied relationships and any claimed rendered output has actually been inspected.

Stop and report when: essential relationship meanings are unknown; show the known structure and identify missing semantics.

## Inputs

Use the entities, relationship meanings, direction, audience, intended medium, and supplied source diagram if any.

## Decision rules

- If the task is sequence or state change, choose that representation instead of a generic box diagram.
- If uncertainty affects an edge, encode it with a labeled convention rather than implying a known fact.
- If a diagram is too dense to read, separate views by the question each answers.
- If rendering tools are unavailable, supply editable source and explicitly label the visual inspection unverified.

## Required procedure

1. Define the meaning of nodes, edges, and direction.
2. Author a small readable diagram in a supported editable format.
3. Inspect any rendered view for clipping, label readability, and semantic consistency.

## Constraints (set by: operator)

- Do not claim image inspection from source syntax alone. Instead, distinguish structural checks from visual checks.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
