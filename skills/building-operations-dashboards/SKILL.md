---
name: building-operations-dashboards
description: "Build an operational dashboard connecting service health, bottlenecks, and changes to concrete operator actions. Use for monitoring dashboards in a supplied platform or schema; a general business presentation or decorative metrics mockup is outside scope."
---

# Building Operations Dashboards

## Purpose

Build an operational dashboard connecting service health, bottlenecks, and changes to concrete operator actions.

## Deliverable

Return an editable dashboard definition, queries and units, variables, threshold rationale, and validation status.

Done when: panels answer named questions and queries, empty states, and time ranges behave coherently.

Stop and report when: live data or import access is absent; deliver the definition while marking runtime checks unverified. Continue independent work and identify the specific blocked action.

## Inputs

Target platform, existing dashboard examples, metric schema, service objectives, and operator questions.

## Decision rules

- Choose panels from operator decisions before arranging the layout.
- Separate throughput, latency, saturation, and availability to avoid misleading shared scales.
- Treat no data as distinct from healthy.

## Required procedure

1. Inspect platform schema and representative metric series.
2. Build an overview and drill-down panels preserving service and time filters.
3. Validate structure and queries, then inspect populated and empty rendering.

## Constraints (set by: operator)

Discover actual platform tools; do not invent metric names or claim an import without evidence. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
