---
name: maintaining-extension-catalogs
description: "Validate and update an existing community extension catalog from a concrete submission or release. Use when a submitted extension must be added or revised under repository publishing rules; not for creating extensions from scratch or automatically endorsing their safety."
---

# Maintaining Extension Catalogs

## Purpose

Validate and update an existing community extension catalog from a concrete submission or release.

## Deliverable

Return the catalog and documentation update with validation evidence and unresolved submission defects.

Done when: manifest, release, compatibility metadata, and displayed catalog entry agree.

Stop and report when: the submitted repository or release artifact cannot be verified; identify the blocked action and continue independent work.

## Inputs

Submission, catalog schema, publishing guide, existing entry, release metadata.

## Decision rules

- Discover the real catalog and validation tooling rather than assuming Spec Kit paths.
- A checked submission box is a claim to verify, not release evidence.
- Updating an entry should preserve historical fields and unrelated statistics.
- Accessible downloads do not establish compatibility or security; retain the catalog’s actual verification status.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Inspect publishing requirements, verify manifest and release identity without executing submitted code, update the existing entry in place or add it consistently, then validate JSON and rendered references.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
