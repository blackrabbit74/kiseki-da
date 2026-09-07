---
name: comparing-options
description: "Compares credible alternatives for a consequential decision using explicit criteria, evidence, tradeoffs, and conditions that would reverse the recommendation. Use when choosing among strategies, concepts, vendors, or approaches; not for a simple factual lookup."
---

# Comparing Options

## Purpose

Help the user make a decision whose reasoning remains understandable when assumptions change.

## Deliverable

Return the decision, relevant options including the status quo when viable, a comparison table, recommendation, strongest dissent, and reversal conditions.

Done when: the recommendation follows from stated priorities and shows which uncertain assumptions could change the preferred option.

Stop and report when: a missing priority makes the options incomparable; ask about that priority and present the known tradeoffs.

## Inputs

Use the choice, decision owner, constraints, timing, alternatives, and available evidence.

## Decision rules

- If options differ only cosmetically, replace them with alternatives that change a meaningful consequence.
- If numerical weights are supplied, show them and test whether reasonable changes reverse the result.
- If current facts determine the choice, verify them before recommending.
- If no evidence distinguishes options, state the tie and name the cheapest discriminating test.

## Required procedure

1. Define the decision and binding constraints.
2. Compare each option on the same criteria and preserve the strongest counterargument.
3. Recommend a course when asked for judgment; distinguish recommendation from the user’s decision.

## Constraints (set by: operator)

- Do not treat simulated advisor agreement as independent evidence. Instead, ground the comparison in observations and explicit assumptions.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
