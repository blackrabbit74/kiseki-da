---
name: extracting-insights
description: "Extracts the important ideas, evidence, disagreements, and usable implications from supplied text or transcripts. Use to summarize a document, interview, article, or recording transcript; new external research is a separate scope unless requested."
---

# Extracting Insights

## Purpose

Preserve the useful meaning of supplied material without inflating what it proves.

## Deliverable

Return a concise synthesis shaped by the material, key insights with locations, important qualifications, and clearly separated implications.

Done when: the main argument and material exceptions remain intact, and attributed statements can be located in the input.

Stop and report when: the content is unavailable or incomplete; state the actual coverage rather than summarizing a title.

## Inputs

Use the supplied document or transcript, desired depth, audience, and intended use.

## Decision rules

- If a transcript has speaker or timestamp uncertainty, keep that uncertainty with the extracted point.
- If sources disagree, retain the disagreement instead of blending it into consensus.
- If adding a practical implication, label it as analysis rather than attributing it to the source.
- If the source has no support for a requested theme, say so rather than inventing a section.

## Required procedure

1. Identify the source’s purpose and central claims.
2. Extract supporting details and qualifications with locations.
3. Compress around the reader’s intended use while preserving the limits of the material.

## Constraints (set by: operator)

- Do not treat a persuasive speaker’s claims as verified facts. Instead, attribute them and distinguish external verification from extraction.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
