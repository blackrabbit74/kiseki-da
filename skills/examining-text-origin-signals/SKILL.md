---
name: examining-text-origin-signals
description: "Examine writing patterns and embedded Unicode features while clearly separating observations from authorship claims. Use when a user asks whether text appears machine-generated or contains hidden characters; not for plagiarism detection, rewriting to evade detectors, or proving an author\u2019s identity."
---

# Examining Text Origin Signals

## Purpose

Examine writing patterns and embedded Unicode features while clearly separating observations from authorship claims.

## Deliverable

Return separate stylistic, statistical, and character-level observations with locations and limitations.

Done when: every reported anomaly is reproducible and no detector score is presented as authorship proof.

Stop and report when: an external detector is requested but authorized access is unavailable; identify the blocked action and continue independent work.

## Inputs

Original text or bytes, language and genre, comparison samples, requested analysis modes.

## Decision rules

- Short or genre-mismatched samples can make detector scores misleading; comparable human baselines reveal calibration problems.
- Invisible characters may have legitimate linguistic or formatting uses; identify code points before interpreting intent.
- A character anomaly does not prove an AI watermark, and keyless scans cannot validate every statistical watermark.
- Keep writing quality separate from apparent origin.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Preserve original bytes, inspect relevant patterns and code points, and use any available authorized detector only with documented current behavior and limitations.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
