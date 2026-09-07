---
name: testing-concepts
description: "Creates a small disposable prototype or walkthrough to answer a concrete design uncertainty and records observations. Use for a concept test, logic demonstration, experience mockup, or JRPG encounter probe before investing in production detail."
---

# Testing Concepts

## Purpose

Answer one uncertain design question with an inspectable probe.

## Deliverable

Return the test question, disposable artifact or walkthrough, reproduction instructions, observations, verdict, and remaining limits.

Done when: the probe exercises the disputed behavior and the verdict follows from recorded observations; unrun probes are labeled untested.

Stop and report when: the question needs unavailable participants, access, or capabilities; deliver the prepared probe and specify the missing execution.

## Inputs

Use the uncertainty, constraints, existing concept, target audience, and available prototype tools.

## Decision rules

- If the uncertainty is experiential, use an interactive mockup or concrete walkthrough; if logical, expose state transitions.
- If testing a JRPG loop, isolate one meaningful encounter or exploration choice with visible cost and consequence.
- If tool execution is outside scope, prepare a paper test and distinguish it from observed play.
- If the answer is already decisive, stop expanding the prototype.

## Required procedure

1. Name the question and what evidence would change the decision.
2. Build the smallest runnable or walkable probe with disposable state.
3. Exercise contrasting cases and record what happened separately from interpretation.

## Constraints (set by: operator)

- Do not promote a successful prototype into production or publish it without that scope. Instead, hand off the observed result and limitations.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
