---
name: reviewing-literature
description: "Finds, screens, and synthesizes a body of academic or technical literature with a reproducible search log and study-level evidence. Use for a literature review, evidence map, or state-of-the-art synthesis; distinguish scoped reviews from systematic reviews."
---

# Reviewing Literature

## Purpose

Explain what a body of literature supports, where it conflicts, and where evidence is missing.

## Deliverable

Return the research question, review scope, search log, inclusion rules, screened-source disposition, evidence table, thematic synthesis, gaps, and verified citations.

Done when: included studies meet stated criteria and each synthesis claim traces to inspected study evidence.

Stop and report when: database or full-text access prevents the requested rigor; offer the supported scope and name excluded checks.

## Inputs

Use the question, review type, population or corpus, date and language limits, and accessible literature sources.

## Decision rules

- If rigor is unspecified, use a scoped review and state its limits.
- If duplicate versions exist, reconcile them and distinguish preprints, published studies, corrections, and retractions.
- If studies use incompatible populations or metrics, compare them separately rather than pooling unsupported numbers.
- If only an abstract is available, mark its extraction limit and avoid claims requiring the unseen methods.

## Required procedure

1. Specify queries and inclusion rules before screening.
2. Log searches, deduplicate records, and record exclusion reasons.
3. Extract design, sample, method, comparator, outcome, and limitations, then synthesize by theme.

## Constraints (set by: operator)

- Do not claim systematic-review coverage from an informal search. Instead, report the databases, dates, and screening actually completed.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
