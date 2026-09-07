---
name: designing-reusable-prompts
description: "Design or refine a prompt or prompt template around testable output requirements and explicit inputs. Use for system prompts, evaluation judges, or programmatic prompt composition; the deliverable is a prompt, not the final domain content requested inside it."
---

# Designing Reusable Prompts

## Purpose

Design or refine a prompt or prompt template around testable output requirements and explicit inputs.

## Deliverable

Return the prompt, variable definitions, assumptions, and representative rendered examples or evaluation cases.

Done when: the prompt expresses the desired result and constraints without contradictory instructions or unresolved template variables.

Stop and report when: an unknown target interface prevents a compatible rendered prompt; deliver portable content and identify the missing contract. Continue independent work and identify the specific blocked action.

## Inputs

Target task, audience or model interface, output schema, example inputs, observed failure cases, and template engine if used.

## Decision rules

- Describe observable success before prescribing a reasoning sequence.
- Keep user-supplied data separate from instruction structure and escape it for the actual template context.
- Retain procedural detail only when tool contracts, output formats, or verified failure modes require it.

## Required procedure

1. Identify input variables and failure-sensitive requirements.
2. Compose concise instructions with examples that expose edge behavior.
3. Render representative and missing-value inputs; check variable resolution, output expectations, and contradictions.

## Constraints (set by: operator)

Do not claim performance improvements without comparison results or embed speculative model-specific rules. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
