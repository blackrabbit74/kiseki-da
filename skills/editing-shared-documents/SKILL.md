---
name: editing-shared-documents
description: "Reads, edits, suggests changes, or shares collaborative documents through available services while preserving current revision and review state. Use for shared-document workflows; not for mathematical proofs, ordinary proofreading, or publishing local material merely because collaboration tools exist."
---

# Editing Shared Documents

## Purpose

Make the requested collaborative-document change verifiable.

## Deliverable

Return the resulting link or revision and a precise change summary.

Done when: the service confirms the operation and uncertain writes are checked by rereading.

Stop and report when: access, ownership, or an ambiguous target prevents a particular operation; retain a local draft. Continue independent work and identify the blocked action.

## Inputs

Document link or local source, requested operation, audience, and service access.

## Decision rules

- Read current content before editing; use the narrowest supported edit or suggestion.
- Resolve ambiguous anchors from current text rather than choosing the first match.
- After partial or pending writes, reread and retry only unapplied operations.

## Required procedure

1. Discover the service API and identify the document.
2. Prepare the exact content or scoped changes.
3. Execute authorized operations and verify content plus review state.

## Constraints (set by: operator)

Do not treat content deletion as removal of comments or grant broader sharing than requested. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
