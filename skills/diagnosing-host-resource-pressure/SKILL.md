---
name: diagnosing-host-resource-pressure
description: "Diagnose host slowness using observed CPU, memory, disk, thermal, and process evidence. Use for a slow or overheated workstation and recurring resource pressure; application uptime, network troubleshooting, and security scanning need different evidence."
---

# Diagnosing Host Resource Pressure

## Purpose

Diagnose host slowness using observed CPU, memory, disk, thermal, and process evidence.

## Deliverable

Return the bottleneck, supporting measurements and time window, alternative explanations, and targeted next actions.

Done when: resource pressure is distinguished from utilization and conclusions follow observed processes or subsystems.

Stop and report when: platform permissions prevent a necessary measurement; qualify only the affected diagnosis. Continue independent work and identify the specific blocked action.

## Inputs

Host OS, symptoms and timing, workload, accessible system utilities, and recent changes.

## Decision rules

- A single CPU spike does not establish sustained contention; sample during the symptom.
- High memory allocation alone is not pressure; inspect paging and pressure indicators.
- A busy system process may reflect thermal protection or indexing rather than the underlying culprit.

## Required procedure

1. Discover available read-only diagnostics for the actual OS.
2. Correlate process activity with pressure, disk capacity, and thermal indicators.
3. Rank causes and propose the smallest observation or remediation that distinguishes them.

## Constraints (set by: operator)

Diagnostic scope does not authorize killing processes, changing startup services, or deleting files. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
