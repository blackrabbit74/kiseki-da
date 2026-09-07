---
name: preparing-model-serving-handoffs
description: "Prepare and verify a model-serving handoff for an actually available compute backend and authorized workload. Use when the user needs serving readiness or an inference manifest for existing compute; not for inventing unsupported serving commands or silently booking paid resources."
---

# Preparing Model Serving Handoffs

## Purpose

Prepare and verify a model-serving handoff for an actually available compute backend and authorized workload.

## Deliverable

Return a serving manifest and capability/eligibility evidence, plus execution status only if authorized and supported.

Done when: model revision, resource fit, exposure, limits, and health checks are explicit; a live claim has endpoint evidence.

Stop and report when: the real backend lacks serving support or verified workload eligibility; identify the blocked action and continue independent work.

## Inputs

Backend identity, existing allocation, model revision, topology, storage, endpoint requirements, cost boundary.

## Decision rules

- Discover current official capabilities; an old scaffold is neither proof of support nor proof of permanent unavailability.
- Node addresses or a quote do not establish allocation ownership or serving entitlement.
- Bind execution to the reviewed workload identity and avoid duplicate creation after ambiguous responses.
- Process start is not endpoint readiness; verify model identity and a bounded inference request.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Inspect available tools and backend documentation, prepare the exact manifest, verify current allocation and resource compatibility, and perform only supported authorized operations with bounded status checks.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
