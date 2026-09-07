---
name: researching-with-sources
description: "Investigates a bounded question using primary sources and produces findings with claim-level citations and explicit uncertainty. Use for factual, technical, or domain research where the user needs traceable evidence rather than a summary of supplied material."
---

# Researching With Sources

## Purpose

Answer a question with evidence the reader can follow back to its origin.

## Deliverable

Return the answer, scope and as-of date, supported findings, conflicting evidence, implications, source links, and unresolved questions.

Done when: each material factual claim is linked to inspected evidence and the conclusion stays within the checked scope.

Stop and report when: the sources needed for the main conclusion remain inaccessible; state what can and cannot be concluded.

## Inputs

Use the question, intended decision, relevant geography or version, time scope, supplied sources, and accessible search tools.

## Decision rules

- If a claim may have changed, verify it against a current authoritative source.
- If a secondary account cites a study, specification, or dataset, inspect that primary source before adopting the claim.
- If sources conflict, compare methods, definitions, dates, and scope instead of choosing by count.
- If further searching no longer changes the answer, finish and expose the remaining uncertainty.

## Required procedure

1. Bound the question and identify the evidence required to answer it.
2. Search and inspect sources, recording which claim each supports.
3. Synthesize the answer and separate fact, inference, and recommendation.

## Constraints (set by: operator)

- Do not cite search snippets or unseen pages as if their contents were inspected. Instead, mark discovery leads and access limits.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
