---
name: retrieving-context
description: "Retrieves the smallest relevant context from an available document or repository collection, refining queries around actual gaps. Use when prior decisions, terminology, or evidence must be located before analysis; not for unrestricted global memory search."
---

# Retrieving Context

## Purpose

Supply the relevant evidence and history without flooding the task with unrelated material.

## Deliverable

Return a context packet with the question, relevant excerpts and locations, dates or versions, resolved gaps, and remaining missing context.

Done when: the packet supports the specified next decision or explicitly identifies what the accessible collection cannot answer.

Stop and report when: further query refinement yields no relevant evidence or access boundaries exclude the needed source; report the remaining gap.

## Inputs

Use the current question, permitted collection, known terms, project identity, and any known source pointers.

## Decision rules

- If a result is from another project or superseded version, verify applicability before using it.
- If the first query fails, refine using discovered vocabulary or likely document roles.
- If a source has dependent context, include the smallest adjacent passage needed to interpret it.
- If the question is answered, stop expanding the context packet.

## Required procedure

1. Define the specific information needed for the next decision.
2. Search likely authoritative locations, then read the matching passages.
3. Refine only unresolved gaps and return attributable context.

## Constraints (set by: operator)

- Do not infer missing history from a file name or empty search. Instead, distinguish not found from did not happen.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
