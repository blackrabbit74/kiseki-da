---
name: drafting-questionnaires
description: "Drafts an answerable questionnaire for a third party whose knowledge is needed for a decision. Use for customer discovery, stakeholder interviews, expert consultation, or asynchronous fact gathering; preparing questions does not imply sending them."
---

# Drafting Questionnaires

## Purpose

Obtain the specific knowledge gap a recipient can resolve.

## Deliverable

Return a ready-to-use questionnaire with purpose, recipient context, answer instructions, prioritized single-focus questions, answer spaces, and room for unknowns.

Done when: every information need has an answerable question and each question can change an identified decision.

Stop and report when: the recipient’s role or needed decision is unknown; ask about that missing sending context.

## Inputs

Use who will answer, what they know, the decision to support, existing answers, and time constraints.

## Decision rules

- If the user lacks subject knowledge, ask about recipient and desired outcome rather than interrogating the user on the missing subject.
- If asking about behavior, request a recent concrete instance before an opinion.
- If a question suggests the desired answer, rewrite it neutrally.
- If recipient time is limited, place the questions with the greatest decision value first.

## Required procedure

1. Map the knowledge gap to the recipient’s experience.
2. Draft one idea per question with an appropriate answer format.
3. Remove duplicates and allow partial answers or explicit uncertainty.

## Constraints (set by: operator)

- Do not send the questionnaire or choose new recipients from a drafting request. Instead, provide the reviewable draft.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
