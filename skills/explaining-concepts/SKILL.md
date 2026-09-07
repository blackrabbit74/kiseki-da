---
name: explaining-concepts
description: "Reframes a difficult concept for a particular reader using a clear mental model, a concrete example, and explicit limits. Use when an explanation did not land, the user asks why something works, or terminology blocks understanding."
---

# Explaining Concepts

## Purpose

Give the reader enough understanding to make the next distinction or decision.

## Deliverable

Return the central idea, necessary context, one concrete example, and the boundary where a simplification stops being accurate.

Done when: the explanation addresses the actual point of confusion and introduces terms before depending on them.

Stop and report when: the referenced concept or confusing passage is unavailable; identify what needs explaining.

## Inputs

Use the reader’s question, prior explanation, existing domain vocabulary, and known background.

## Decision rules

- If the user says they do not understand, change the framing rather than repeat the same jargon.
- If an analogy helps, map its parts to the real system and name where it breaks.
- If the topic is a dependency or flow, use a small diagram only when it resolves the confusion.
- If the user wants to learn, offer a discriminating example or prompt before a worked solution when appropriate.

## Required procedure

1. Locate the missing concept or mistaken relationship.
2. Explain it in familiar terms using the project’s established vocabulary.
3. Connect the example back to the user’s original question.

## Constraints (set by: operator)

- Do not simplify by making a false universal claim. Instead, state the relevant condition or exception.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
