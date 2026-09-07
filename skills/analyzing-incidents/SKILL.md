---
name: analyzing-incidents
description: "Builds an evidence-based incident review connecting timeline, impact, contributing conditions, and recurrence-prevention actions. Use after outages or recurring operational failures; not for live incident command or reducing complex events to blame on one person."
---

# Analyzing Incidents

## Purpose

Explain why the incident became possible and how recurrence risk changes.

## Deliverable

Return timeline, impact, causal evidence, uncertainties, and prioritized preventive actions.

Done when: actions address supported contributing factors and have owners or proposed ownership plus validation.

Stop and report when: missing records prevent attributing a particular causal link. Continue independent work and identify the blocked action.

## Inputs

Incident records, logs, decisions, impact measurements, and operating context.

## Decision rules

- Separate trigger, contributing conditions, detection gaps, and recovery factors.
- Evaluate decisions using information available at the time.
- Do not force a fixed number of causes; stop causal depth where evidence and actionable change meet.

## Required procedure

1. Reconstruct a timestamped timeline with sources.
2. Test the causal account against alternatives and missing evidence.
3. Prioritize prevention, detection, and recovery changes with success checks.

## Constraints (set by: operator)

Avoid blame labels and invented certainty; a proposed action is not an implemented control. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
