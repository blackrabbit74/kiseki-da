---
name: exploring-ideas
description: Explores vague topics or raw ideas by grounding them in available context, generating distinct options, critiquing every candidate, and helping the user select promising directions. Use when the user asks to brainstorm, ideate, improve an idea, discover alternatives, or stress-test possibilities before planning or implementation.
---

# Exploring Ideas

## Purpose

Turn a vague topic or idea into distinct options and promising directions. End with selection material.

## Deliverable

Return a concise Idea brief in the conversation unless the user requests Markdown. Include:

- Framing: subject, outcome, audience, and constraints.
- Options: five to eight meaningfully different candidates.
- Critique: a disposition and reason for every candidate.
- Directions: two or three survivors with tradeoffs and failure conditions.
- Assumptions: unsupported claims and ways to test them.
- Decision: the user's choice or an unresolved state.

Done when: every candidate has a reasoned disposition, assumptions are separated from evidence, and the user's decision or unresolved state is recorded.

Stop and report when: the subject or outcome is unidentified, required context is inaccessible, or the user pauses. State what is missing and how to resume.

## Inputs

Use the topic, intended outcome, audience, constraints, and permitted relevant materials.

## Decision rules

- If missing information changes the options, ask one concise question at a time.
- If relevant material exists, read only what grounds the options before generating them.
- If refining an idea, vary its assumptions, constraints, audience, combinations, and simplest form.
- If more breadth is requested, continue in small batches.
- If narrowing is requested, critique every candidate before clustering survivors and recommending a direction.

## Required procedure

1. Frame the subject, outcome, audience, constraints, and grounding.
2. Generate initial options before critiquing any.
3. Critique each for value, feasibility, constraint fit, and difference.
4. Cluster survivors with tradeoffs, assumptions, and failure conditions.
5. Record the choice, parked and rejected options, and next test.

## Constraints (set by: operator)

- Do not start planning or implementation unless the user asks after reviewing the directions. Instead, stop at the brief. (Set by the operator; follow it.)
- Do not save, send, or execute changes unless requested and permitted. Instead, return the brief in conversation. (Set by the operator; follow it.)

## Model notes

- Claude: Identify options by criteria without private taxonomy labels.
- GPT: State success criteria and approval boundaries once; follow the user.
