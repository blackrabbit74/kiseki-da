---
name: instrumenting-service-operations
description: "Add or improve logs, metrics, traces, and actionable alerts for service operations. Use when operators cannot explain production behavior or need to observe a new integration; a full incident response or speculative performance rewrite is outside this workflow."
---

# Instrumenting Service Operations

## Purpose

Add or improve logs, metrics, traces, and actionable alerts for service operations.

## Deliverable

Return instrumentation changes or configuration, signal-to-question mapping, sample queries, and verification evidence.

Done when: each signal answers an operating question and its fields, scope, and failure behavior can be demonstrated.

Stop and report when: a telemetry backend cannot be reached; withhold claims of ingestion or live alert delivery. Continue independent work and identify the specific blocked action.

## Inputs

Service boundaries, operating questions, telemetry stack, traffic patterns, privacy limits, and service objectives.

## Decision rules

- Use metrics for aggregate rates, logs for events, and traces for cross-service latency.
- Propagate correlation and entry-point identity to distinguish scheduled, replayed, and manual executions.
- Avoid user identifiers as metric labels; bound cardinality and redact sensitive payloads.

## Required procedure

1. Define success and failure questions for the target path.
2. Implement signals with stable names and connect alerts to an owner action.
3. Exercise success and failure cases; check correlation, missing data, and queries.

## Constraints (set by: operator)

Do not infer health from absent telemetry or send test alerts to people without authorization. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
