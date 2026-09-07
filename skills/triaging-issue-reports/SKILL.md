---
name: triaging-issue-reports
description: "Evaluate issues or pull-request reports into evidence-backed classifications and implementation-ready briefs. Use for backlog triage, reproducibility checks, or missing-information diagnosis; it does not itself authorize posting comments, closing issues, or merging code."
---

# Triaging Issue Reports

## Purpose

Evaluate issues or pull-request reports into evidence-backed classifications and implementation-ready briefs.

## Deliverable

Return category, recommended state, reproduction evidence, existing implementation or duplicates, and an actionable brief.

Done when: recommendations follow inspected history and distinguish confirmed behavior from unresolved claims.

Stop and report when: missing access or reproduction inputs prevent verifying a claim; preserve remaining triage findings. Continue independent work and identify the specific blocked action.

## Inputs

Report body, comments, labels, linked work, relevant code, tracker conventions, and requested actions.

## Decision rules

- Search by domain behavior before classifying a request as new; existing implementation differs from rejection.
- A PR includes code evidence, but its claimed behavior still needs verification.
- Read prior answers before requesting information; preserve explicit maintainer overrides.

## Required procedure

1. Gather report history and project terminology.
2. Reproduce the issue or inspect the diff and classify evidence.
3. Draft scope, acceptance conditions, dependencies, and missing inputs; apply only authorized tracker changes.

## Constraints (set by: operator)

Discover actual tracker labels; do not impose another project’s state machine or send unsolicited messages. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
