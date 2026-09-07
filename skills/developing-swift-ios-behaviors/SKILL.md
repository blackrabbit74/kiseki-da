---
name: developing-swift-ios-behaviors
description: "Implement and verify Swift or iOS behavior using actor isolation, persistence contracts, and available simulator evidence. Use when Swift state, storage, or app interactions need development or repair; not for assuming an Xcode MCP adapter exists or treating a build as full UI verification."
---

# Developing Swift Ios Behaviors

## Purpose

Implement and verify Swift or iOS behavior using actor isolation, persistence contracts, and available simulator evidence.

## Deliverable

Return the change with project, scheme, target, build result, interaction evidence, and explicit skipped checks.

Done when: affected behavior has passing evidence and any untested device capability is identified.

Stop and report when: the required Xcode runtime, scheme, or simulator is unavailable; identify the blocked action and continue independent work.

## Inputs

Swift language mode, project/scheme, actor boundaries, persistence format, target interactions.

## Decision rules

- Actor isolation does not make a multi-step operation atomic across await; recheck assumptions after suspension.
- Update cache and disk consistently when persistence fails; atomic file replacement alone does not roll back memory.
- Distinguish absent storage from corrupt or incompatible data instead of silently treating every read failure as empty.
- Simulator evidence cannot establish every physical-device capability.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Discover available build and interaction tools, implement the bounded behavior, and verify concurrent access, failed writes, relaunch, and affected screens with logs.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
