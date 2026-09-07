---
name: defining-domain-terms
description: "Clarifies domain terms and records substantive decisions with their context, alternatives, and consequences. Use when terminology is overloaded, project concepts conflict, or a lasting decision needs a glossary entry or decision record."
---

# Defining Domain Terms

## Purpose

Give collaborators stable meanings and a traceable reason for important choices.

## Deliverable

Return the relevant glossary entries and, when warranted, decision records containing context, alternatives, status, rationale, consequences, and superseded decisions.

Done when: ambiguous terms have examples and boundaries; each recorded decision distinguishes a proposal from an accepted choice.

Stop and report when: two authoritative meanings conflict and the available context cannot resolve them; preserve both with the affected scope.

## Inputs

Use existing glossaries, decisions, domain examples, and implementation or story canon where relevant.

## Decision rules

- If one term denotes different concepts, name the concepts separately and test them with edge cases.
- If a claim conflicts with code or supplied canon, report the mismatch rather than rewriting history.
- If a choice has no lasting tradeoff, keep a brief note instead of manufacturing an ADR.
- If a decision changes, link the replacement while retaining the old rationale.

## Required procedure

1. Find existing definitions before proposing vocabulary.
2. Test a disputed definition against an example and counterexample.
3. Record the resolved meaning and only the decisions needed to explain consequences.

## Constraints (set by: operator)

- Do not silently mark an inferred decision as approved. Instead, preserve its proposed or unresolved status.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
