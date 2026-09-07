---
name: analyzing-assumptions
description: "Examines assumptions and causal explanations behind a problem, separating observations, constraints, and beliefs and identifying tests or interventions. Use when a proposal depends on hidden premises, a repeated symptom, or interacting feedback loops."
---

# Analyzing Assumptions

## Purpose

Identify which assumptions or causal links are actually carrying a proposed explanation.

## Deliverable

Return a problem decomposition, an evidence and assumption table, competing explanations, a causal map when useful, and discriminating tests.

Done when: each important causal claim names supporting evidence or a test, and alternative explanations remain visible.

Stop and report when: the observation being explained is unavailable; report the missing measurement and limit the conclusion.

## Inputs

Use observed symptoms, measurements, stated constraints, stakeholder explanations, and the boundary of the system.

## Decision rules

- If a constraint comes from the user, contract, or policy, retain it as binding unless its owner changes it.
- If a causal link is inferred from correlation, identify a confounder or reverse-causation possibility.
- If changing one variable affects others, include feedback, delay, and effects outside the immediate boundary.
- If proposing an intervention, identify what observation would contradict its mechanism.

## Required procedure

1. Separate observations, interpretations, inherited conventions, and binding constraints.
2. Construct the strongest plausible competing explanation.
3. Identify the smallest observation or intervention that distinguishes explanations.

## Constraints (set by: operator)

- Do not treat only physical limits as binding or silently relax user constraints. Instead, separate challengeable beliefs from authorized boundaries.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
