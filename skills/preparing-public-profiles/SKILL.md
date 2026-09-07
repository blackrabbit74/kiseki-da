---
name: preparing-public-profiles
description: "Prepare or update a public profile from user-selected material with explicit provenance and disclosure boundaries. Use when the user wants a current professional profile or public-facing activity summary; not for broad private-data aggregation or automatic publication."
---

# Preparing Public Profiles

## Purpose

Prepare or update a public profile from user-selected material with explicit provenance and disclosure boundaries.

## Deliverable

Return a reviewable profile draft or data artifact, source mapping, and changes from the previous public version.

Done when: all included claims are supportable and intended for the target audience.

Stop and report when: a proposed disclosure is not covered by the user’s public-sharing intent; identify the blocked action and continue independent work.

## Inputs

Approved sources, audience, existing profile, current activities, publication scope.

## Decision rules

- Prefer selecting approved fields before transformation; regex filtering alone cannot establish disclosure suitability.
- Remove internal paths, credentials, private contacts, and incidental third-party details from public artifacts.
- Time-sensitive status needs a date or expiry so old activity does not remain current.
- Draft preparation and live publication are separate actions; use existing authorization when publication was requested.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Map approved content to public claims, produce the requested format, and inspect both visible output and underlying data for unintended disclosures.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
