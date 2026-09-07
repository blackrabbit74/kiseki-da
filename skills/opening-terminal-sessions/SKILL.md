---
name: opening-terminal-sessions
description: "Prepare and launch a requested interactive terminal session with an exact executable, argument list, and working directory. Use for development servers, SSH, or interactive CLIs in a visible terminal; routine non-interactive commands do not require this workflow."
---

# Opening Terminal Sessions

## Purpose

Prepare and launch a requested interactive terminal session with an exact executable, argument list, and working directory.

## Deliverable

Return the launch specification, terminal capability, session identity or supported fallback, and observed startup state.

Done when: arguments and working directory are preserved and actual launch status differs clearly from a proposed plan.

Stop and report when: no supported adapter exists or startup fails; return a usable launch specification. Continue independent work and identify the specific blocked action.

## Inputs

Requested terminal, executable, arguments, working directory, environment needs, and launch intent.

## Decision rules

- Preserve arguments separately; avoid interpolating them into shell strings.
- A detached fallback must preserve requested interaction and visibility.
- Recovery that ignores configuration changes behavior; use it only for relevant diagnosed failures.

## Required procedure

1. Discover the terminal API and inspect executable and directory.
2. Compose the launch with minimal environment exposure and use existing launch authorization.
3. Read startup state and report the session or exact recoverable failure.

## Constraints (set by: operator)

Do not pass a full secret-bearing environment unnecessarily or silently substitute another application. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
