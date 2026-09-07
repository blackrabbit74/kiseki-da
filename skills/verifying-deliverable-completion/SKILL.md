---
name: verifying-deliverable-completion
description: "Checks a deliverable against explicit acceptance conditions and reports claims supported by current evidence. Use for completion audits or handoff verification; not for rerunning unrelated checks indefinitely or treating a successful build as proof of every requirement."
---

# Verifying Deliverable Completion

## Purpose

Make completion claims match what was actually verified.

## Deliverable

Return an acceptance-to-evidence mapping, failures, and material unverified conditions.

Done when: each completion claim names adequate evidence for the current artifact.

Stop and report when: a required check cannot run because access or environment is unavailable. Continue independent work and identify the blocked action.

## Inputs

Deliverable, acceptance criteria, previous check results, and relevant tools.

## Decision rules

- Match the check to the claim: build, behavior, requirements, and visual fidelity prove different things.
- Reuse valid evidence unless changes or uncertainty invalidate it.
- An agent report is a lead; inspect its actual artifact and relevant checks.

## Required procedure

1. Enumerate concrete acceptance claims.
2. Run missing checks and inspect their outputs and exit status.
3. Report verified completion and exact limitations without extrapolation.

## Constraints (set by: operator)

Do not replace a failing requirement with a weaker definition of done. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
