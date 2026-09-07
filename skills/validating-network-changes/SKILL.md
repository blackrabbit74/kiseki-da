---
name: validating-network-changes
description: "Inspect router and switch changes and diagnose BGP failures using operational evidence. Use when reviewing network configurations or missing routes; not for generic application connectivity debugging."
---

# Validating Network Changes

## Purpose

Inspect router and switch changes and diagnose BGP failures using operational evidence.

## Deliverable

Return findings by device, VRF, address family, configuration location, impact, and evidence.

Done when: expected routes and management reachability are checked, with untested platform behavior explicit.

Stop and report when: device identity or recovery access is missing for a live change; identify the blocked action and continue independent work.

## Inputs

Topology, platform/version, current and proposed configuration, peer state, intended prefixes, and change scope.

## Decision rules

- BGP Established proves session health, not correct route exchange; compare advertised, accepted, and installed routes.
- Evaluate address overlaps within routing domains; identical addresses across separate VRFs may be valid.
- Check policy definitions and references together; management authentication changes can remove recovery access.
- Do not reset peers or weaken ACLs merely to collect diagnostic evidence.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Review destructive commands, management access, addressing, and route policy; validate syntax against the actual platform and compare before/after evidence.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
