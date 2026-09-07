---
name: synthesizing-documents
description: "Synthesizes supplied documents into a coherent working brief while preserving provenance, conflicting variants, and unresolved decisions. Use when integrating project notes, consulting inputs, requirements, or story canon; not for silently choosing authority by file type."
---

# Synthesizing Documents

## Purpose

Create one usable view of a document set without concealing disagreements.

## Deliverable

Return an input inventory, consolidated brief, provenance for material claims, superseded content, unresolved conflicts, and gaps.

Done when: material inputs have a disposition and every resolved conflict cites the authority or explicit instruction used.

Stop and report when: equally authoritative commitments conflict; preserve both and identify the affected portion while synthesizing independent material.

## Inputs

Use the supplied documents, versions, project scope, known authorities, and the requested destination format.

## Decision rules

- If precedence is explicitly defined, apply it within its scope; otherwise compare author, status, date, and user instructions.
- If a newer document only proposes a change, preserve the accepted baseline until the proposal is adopted.
- If two descriptions use different terminology, reconcile meanings before merging them.
- If one source cites another, retain the original provenance and avoid counting it as independent corroboration.

## Required procedure

1. Inventory inputs and their roles, versions, and authority.
2. Extract overlapping claims and distinguish duplicates from genuine conflicts.
3. Synthesize supported content and keep unresolved variants visible.

## Constraints (set by: operator)

- Do not overwrite conflicting accepted decisions with a guessed consensus. Instead, report the conflict and the specific resolution needed.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
