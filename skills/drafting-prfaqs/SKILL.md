---
name: drafting-prfaqs
description: "Tests a proposed product by drafting a future press release and customer and internal FAQs. Use when the user requests working backwards or a PRFAQ to expose gaps in value, adoption, feasibility, and economics."
---

# Drafting Prfaqs

## Purpose

Make the future customer promise concrete enough to expose unsupported assumptions.

## Deliverable

Return a clearly hypothetical press release, customer FAQ, internal FAQ, and a short list of claims requiring validation.

Done when: the release states a concrete customer change, and the FAQs address adoption barriers, alternatives, feasibility, cost drivers, and failure conditions.

Stop and report when: the promised customer outcome is unidentified; return the specific missing premise.

## Inputs

Use the concept, target customer, alternatives, available evidence, and constraints.

## Decision rules

- If using a future quotation or launch result, mark it as fictional illustration.
- If the promise relies on market or competitor facts, check current primary sources.
- If an internal answer is unknown, expose the dependency and a test instead of inventing certainty.
- If the user asks only for a PRFAQ, finish with that artifact rather than starting a PRD pipeline.

## Required procedure

1. Write the customer-visible change as if the proposed product existed.
2. Ask the questions a skeptical customer would need answered before adoption.
3. Challenge the promise from delivery and economic perspectives, then revise inconsistent claims.

## Constraints (set by: operator)

- Do not publish the hypothetical release or claim actual endorsements. Instead, deliver a reviewable concept document.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
