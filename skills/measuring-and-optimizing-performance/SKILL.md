---
name: measuring-and-optimizing-performance
description: "Measures representative performance, identifies bottlenecks, and evaluates targeted optimizations under comparable conditions. Use for latency, resource, build, or responsiveness problems; not for claiming speedups from intuition or running unbounded load against production."
---

# Measuring And Optimizing Performance

## Purpose

Improve the measured bottleneck without hiding correctness costs.

## Deliverable

Return baseline, method, bottleneck evidence, changes, and comparable results.

Done when: the result is reproducible and any gain is distinguished from measurement noise.

Stop and report when: available tooling or load authorization prevents the required measurement. Continue independent work and identify the blocked action.

## Inputs

Workload, environment, performance target, baseline, and permitted load.

## Decision rules

- Separate cold and warm runs and record concurrency, data size, and hardware.
- Compare distributions and error rates rather than averages alone.
- Optimize the constrained path; avoid transferring latency into memory, failures, or user-visible delay.

## Required procedure

1. Define a representative workload and stable baseline.
2. Profile the limiting component and change one meaningful factor.
3. Repeat comparable measurements and verify correctness.

## Constraints (set by: operator)

Do not bake generic performance targets into project requirements. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
