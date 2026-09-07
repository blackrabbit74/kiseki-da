---
name: authoring-task-skills
description: "Create or improve a reusable task skill with precise discovery cues, decision guidance, and observable completion conditions. Use when a recurring workflow needs a maintained SKILL.md package; one-off task execution or generic prompting advice does not automatically need a skill."
---

# Authoring Task Skills

## Purpose

Create or improve a reusable task skill with precise discovery cues, decision guidance, and observable completion conditions.

## Deliverable

Return the skill package, source or behavior rationale, static validation, and clearly labeled behavioral evaluation results when run.

Done when: the entry point routes the intended requests, includes useful non-obvious guidance, and references only actual resources.

Stop and report when: a required source or runtime contract is missing; draft independent guidance and identify the unsupported integration. Continue independent work and identify the specific blocked action.

## Inputs

Target requests, existing skill, observed failures, host format, related skills, and relevant source material.

## Decision rules

- Separate reusable decisions from the story of one successful run.
- Prefer enforceable tooling for mechanical invariants when repeated execution justifies it.
- Evaluate likely false triggers and exclusions alongside successful invocation; do not equate syntax checks with behavior.

## Required procedure

1. Inspect current host authoring guidance and the smallest relevant examples.
2. Write outcome, inputs, conditional decisions, and proportionate limits; add references only for genuinely separate detail.
3. Run available package validation and, when warranted and authorized, realistic baseline/comparison cases.

## Constraints (set by: operator)

Preserve user scope and invocation preferences; do not impose mandatory delegation or installation during authoring. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
