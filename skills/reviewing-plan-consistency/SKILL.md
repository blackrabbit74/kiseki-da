---
name: reviewing-plan-consistency
description: "Reviews consistency across requirements, concepts, designs, and plans by tracing commitments and identifying contradictions, gaps, and unsupported work. Use for a cross-document review before handoff, planning commitment, or a major revision."
---

# Reviewing Plan Consistency

## Purpose

Find contradictions and missing coverage that would cause collaborators to build or decide different things.

## Deliverable

Return findings with source locations, conflicting statements or uncovered commitments, practical impact, and the smallest proposed correction.

Done when: material commitments have a downstream disposition and each finding is supported by identifiable passages.

Stop and report when: a required comparison document is missing; identify which coverage claim cannot be assessed.

## Inputs

Use the requested documents, their versions, stated precedence, and accepted decisions.

## Decision rules

- If two sources disagree, use explicit authority and scope rather than assuming document type determines precedence.
- If a requirement has no implementation or validation path, report the missing link.
- If planned work has no upstream purpose, ask whether it is deliberate scope or an orphan.
- If reviewing story plans, trace world rules, character motives, chapter events, and player actions for contradictions.

## Required procedure

1. Inventory the relevant versions and commitments.
2. Trace each material commitment across the supplied artifacts.
3. Report supported conflicts and coverage gaps in order of practical impact.

## Constraints (set by: operator)

- Do not rewrite reviewed documents when only a review was requested. Instead, provide located corrections.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
