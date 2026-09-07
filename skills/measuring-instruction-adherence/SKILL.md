---
name: measuring-instruction-adherence
description: "Measure whether an agent actually follows applicable skill or workflow instructions using scenarios and execution evidence. Use for instruction adherence and discovery tests; a well-formed skill file or an agent’s self-report is not evidence that the behavior occurred."
---

# Measuring Instruction Adherence

## Purpose

Measure whether an agent actually follows applicable skill or workflow instructions using scenarios and execution evidence.

## Deliverable

Return applicable obligations, scenario prompts, tool or action timelines, adherence findings, denominators, and unobservable steps.

Done when: each scored obligation has an applicability decision and evidence distinct from the agent’s stated intention.

Stop and report when: the runner cannot expose the evidence needed for a score; mark that behavior unobservable and retain the scenario design. Continue independent work and identify the specific blocked action.

## Inputs

Target instructions, instruction hierarchy, representative requests, authorized runner, traces, and grading criteria.

## Decision rules

- Test supportive, neutral, and competing phrasing without treating lower-priority text as overriding user authority.
- Separate skill selection failure from failure after loading.
- Check temporal ordering only where the instruction requires it; avoid inventing a fixed sequence.

## Required procedure

1. Translate applicable instructions into observable obligations and exclusions.
2. Run bounded scenarios and preserve tool traces and resulting artifacts.
3. Classify met, violated, inapplicable, and unobservable obligations; report scenario-level evidence and coverage.

## Constraints (set by: operator)

Do not install enforcement hooks as an automatic response to poor scores or infer compliance from keyword matching alone. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
