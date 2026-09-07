---
name: compiling-local-civic-briefs
description: "Compile dated local news and civic information for a specified jurisdiction from authoritative sources. Use when the user needs a local digest of permits, public meetings, ordinances, elections, or nearby developments; not for national-news summaries or inferring the user\u2019s residence."
---

# Compiling Local Civic Briefs

## Purpose

Compile dated local news and civic information for a specified jurisdiction from authoritative sources.

## Deliverable

Return a concise digest with event and publication dates, jurisdiction, source links, and missing-source coverage.

Done when: items are deduplicated and proposals, decisions, and effective rules are distinguished.

Stop and report when: the target jurisdiction is unknown for location-specific retrieval; identify the blocked action and continue independent work.

## Inputs

City or region, time window, requested categories, preferred public sources.

## Decision rules

- Municipal, county, and regional authorities may govern different topics; verify jurisdiction.
- An agenda item is not an adopted ordinance, and adoption may precede its effective date.
- Source silence does not prove no events occurred.
- Arrest reports are allegations, not findings of guilt; avoid unnecessary private-person details.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Resolve current official portals, gather requested categories, cross-check consequential dates, and mark unavailable sources without losing independent results.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
