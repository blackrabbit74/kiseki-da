---
name: verifying-release-installations
description: "Install a specified released artifact through its distribution channel and verify basic usability in an isolated environment. Use for installer regressions or published binary smoke tests; ordinary source tests and unreleased build validation are separate tasks."
---

# Verifying Release Installations

## Purpose

Install a specified released artifact through its distribution channel and verify basic usability in an isolated environment.

## Deliverable

Return channel, version, platform, artifact hash, executable path, PASS/FAIL/SKIP checks, failure evidence, and cleanup status.

Done when: the actual installed executable is identified and installation, essential behavior, and restoration are individually accounted for.

Stop and report when: an artifact is unavailable, integrity fails, or cleanup would touch resources whose ownership is unclear. Continue independent work and identify the specific blocked action.

## Inputs

Target release, distribution channel, platform, existing installations, smoke scenarios, and permitted temporary environment.

## Decision rules

- Use absolute executable paths to avoid testing a development checkout.
- A successful local build does not prove the published asset works.
- Continue independent checks after failure and retain the overall failure; restore only state this run changed.

## Required procedure

1. Record existing installation state and obtain the exact released asset.
2. Inspect the installer and verify available integrity evidence before isolated execution.
3. Check version/build identity and a meaningful user flow, then clean up and report residual state.

## Constraints (set by: operator)

Do not replace the default installation or remove a remote host merely to run a smoke test. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
