---
name: analyzing-recorded-feedback
description: "Turn supplied screen recordings, audio, transcripts, or feedback bundles into traceable product findings. Use for bug evidence and workflow feedback extraction; general transcription requests should remain transcription, and analysis does not automatically start product planning."
---

# Analyzing Recorded Feedback

## Purpose

Turn supplied screen recordings, audio, transcripts, or feedback bundles into traceable product findings.

## Deliverable

Return issues with timestamps or artifact references, expected versus actual behavior, user intent, and uncertainty.

Done when: each finding can be located in the source and observed behavior differs clearly from proposed requirements.

Stop and report when: a modality cannot be inspected; analyze available evidence and identify unsupported claims. Continue independent work and identify the specific blocked action.

## Inputs

Recording or bundle, transcript and event metadata, product context, and analysis depth.

## Decision rules

- A focused clip usually needs one bug report; a walkthrough may support multiple findings.
- Audio intent and visible behavior can disagree; retain both without inventing interactions.
- If asked only to transcribe, avoid turning remarks into requirements.

## Required procedure

1. Inspect files, duration, and modalities without uploading them by default.
2. Extract the relevant sequence and align screen, audio, and event timestamps.
3. Produce the requested report with source locations and distinguish observations, interpretations, and suggestions.

## Constraints (set by: operator)

Keep raw captures local unless sharing is authorized; never claim to have watched unavailable frames. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
