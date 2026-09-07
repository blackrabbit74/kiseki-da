---
name: preparing-isolated-workspaces
description: "Creates or verifies an isolated Git worktree or checkout while preserving user changes and respecting workspace ownership. Use when work needs isolation or the user requests a separate checkout; not for automatically nesting worktrees or changing a chosen working directory unnecessarily."
---

# Preparing Isolated Workspaces

## Purpose

Provide a known starting state for independent work.

## Deliverable

Return the usable workspace path, branch or revision, setup evidence, and preserved-state notes.

Done when: the workspace resolves to the intended repository state and required setup is verified.

Stop and report when: an ambiguous starting state or inaccessible directory prevents workspace creation. Continue independent work and identify the blocked action.

## Inputs

Repository, starting state, current changes, isolation preference, and native workspace tools.

## Decision rules

- Detect existing linked worktrees and distinguish submodules before creating another.
- Follow explicit starting-state preferences; uncommitted changes require deliberate handling.
- Use supported native workspace management where available and respect externally managed cleanup.

## Required procedure

1. Inspect repository and worktree state.
2. Create or reuse the appropriate isolated workspace.
3. Verify revision, configuration, and a proportionate baseline check.

## Constraints (set by: operator)

Do not discard user changes, silently switch branches, or clean up externally owned worktrees. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
