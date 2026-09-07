---
name: designing-software-architecture
description: "Designs software responsibilities, interfaces, and variation points around concrete use cases and operational constraints. Use for module or subsystem architecture decisions; not for adding speculative abstraction layers or automatically restructuring a working repository."
---

# Designing Software Architecture

## Purpose

Concentrate complexity where callers need to know less.

## Deliverable

Return architecture decisions, responsibilities, interface obligations, alternatives, and verification seams.

Done when: the design supports representative flows and explains consequential tradeoffs.

Stop and report when: an unknown operational constraint prevents selecting a consequential architecture option. Continue independent work and identify the blocked action.

## Inputs

Use cases, existing architecture, expected change, constraints, and consumers.

## Decision rules

- An interface includes ordering, errors, configuration, and performance obligations, not just signatures.
- Ask whether removing an abstraction eliminates complexity or spreads it into callers.
- Introduce variation points for actual differences; avoid layers whose only role is forwarding.

## Required procedure

1. Trace representative flows and likely change boundaries.
2. Compare responsibility and interface choices against constraints.
3. Demonstrate testing and failure handling through the chosen boundaries.

## Constraints (set by: operator)

Use the project’s domain vocabulary rather than forcing a proprietary glossary. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
