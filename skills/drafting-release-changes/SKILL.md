---
name: drafting-release-changes
description: "Compile evidence-backed release notes from a defined change range, highlighting user impact and migration steps. Use for preparing a changelog or release announcement draft; this does not publish releases or certify that distribution artifacts work."
---

# Drafting Release Changes

## Purpose

Compile evidence-backed release notes from a defined change range, highlighting user impact and migration steps.

## Deliverable

Return categorized notes, source PR or commit links, release boundaries, migration notes, and unresolved claims.

Done when: each reported change maps to the selected range and important breaking or security changes are visible.

Stop and report when: release boundaries cannot be resolved or a material claim lacks evidence; hold that claim or final version label. Continue independent work and identify the specific blocked action.

## Inputs

Previous and target revisions, merged changes, direct commits, audience, and established release voice.

## Decision rules

- Put breaking and security changes ahead of routine improvements.
- Omit internal churn unless it changes user behavior or risk; preserve relevant dependency security fixes.
- Describe required user action separately from implementation details.

## Required procedure

1. Resolve the range and collect changes with stable identifiers.
2. Deduplicate related commits and translate verified effects into concise notes.
3. Check links and upgrade instructions; save the draft at the requested destination.

## Constraints (set by: operator)

Publishing requires authorization for that external action; drafting needs no separate approval. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
