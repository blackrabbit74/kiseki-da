---
name: creating-presentation-decks
description: "Creates or revises presentation decks in the requested editable or browser format, connecting narrative, slide hierarchy, and visual verification. Use for talks, pitches, or slide conversion; not for replacing a requested PowerPoint deliverable with HTML without reason."
---

# Creating Presentation Decks

## Purpose

Produce a readable deck that supports the speaker or reader.

## Deliverable

Return the deck, editable source where applicable, and verified rendering.

Done when: slides fit their intended canvas and the argument remains clear at presentation size.

Stop and report when: a required format renderer is unavailable; provide editable content and state the unverified export. Continue independent work and identify the blocked action.

## Inputs

Audience, purpose, duration, content, references, and output format.

## Decision rules

- One slide should carry a discernible takeaway; split dense material rather than shrinking text.
- Honor existing templates and requested format; discover available document tooling.
- Preserve notes and essential relationships during conversion; report unsupported animations.

## Required procedure

1. Outline the narrative and map evidence to slides.
2. Build using appropriate presentation tools and reusable visual rules.
3. Render all slides and correct overflow, illegibility, and navigation problems.

## Constraints (set by: operator)

Do not require multiple style previews when direction is already clear. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
