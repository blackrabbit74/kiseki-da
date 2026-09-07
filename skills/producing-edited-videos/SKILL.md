---
name: producing-edited-videos
description: "Builds edited videos from supplied footage, transcripts, or an explicit composition brief, including cuts, overlays, captions, and export checks. Use for video production or repurposing recordings; not for silently generating replacement footage or imposing a fixed vendor pipeline."
---

# Producing Edited Videos

## Purpose

Turn source material into an intentional, playable sequence.

## Deliverable

Return the video and reproducible timeline or edit decisions where available.

Done when: duration, cuts, captions, framing, and audio synchronization are checked in playback.

Stop and report when: a missing source or renderer prevents producing a particular segment. Continue independent work and identify the blocked action.

## Inputs

Footage, transcript, desired length, audience, aspect ratio, and assets.

## Decision rules

- Choose cuts for narrative value, not only silence removal.
- Stream-copy cuts may be keyframe-limited; use accurate re-encoding when timing requires it.
- Maintain source timestamps separately from edited timeline timestamps.

## Required procedure

1. Inventory media properties and identify useful segments.
2. Build an edit decision list and implement cuts and overlays with available tools.
3. Watch representative transitions and the complete export when feasible; inspect sync and framing.

## Constraints (set by: operator)

Preserve original media and distinguish generated additions from recorded footage. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
