---
name: modeling-system-threats
description: "Models defensive compromise scenarios across assets, sensitive data, credentials, and trust relationships, producing actionable risks. Use for threat modeling or risk-register work on an identified system; not for active exploitation or executing incident-response actions."
---

# Modeling System Threats

## Purpose

Identify how compromise could propagate and which controls change the outcome.

## Deliverable

Return asset and data boundaries, scenarios, prioritized risks, mitigations, and uncertainties.

Done when: important risks connect an attacker capability to reachable impact and a testable control.

Stop and report when: missing inventory prevents judging a particular propagation path. Continue independent work and identify the blocked action.

## Inputs

System architecture, asset inventory, data classes, trust relationships, and operating constraints.

## Decision rules

- Model both dependency access and credentials held by compromised assets.
- Separate observed inventory from assumptions; unknown assets are coverage gaps.
- Anchor likelihood and impact scales; arithmetic scores do not replace scenario reasoning.

## Required procedure

1. Map assets, sensitive data, and trust crossings.
2. Walk plausible compromise paths and existing detection or containment.
3. Prioritize controls and specify how residual risk will be checked.

## Constraints (set by: operator)

Do not treat planning as authorization for exploitation or risk acceptance. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
