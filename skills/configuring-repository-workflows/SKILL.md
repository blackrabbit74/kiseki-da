---
name: configuring-repository-workflows
description: "Configure repository-local integration conventions for installed engineering tools, issue tracking, and domain documentation. Use when a requested tool setup needs to fit existing repository workflows; not for installing an entire harness or rewriting global agent policy."
---

# Configuring Repository Workflows

## Purpose

Configure repository-local integration conventions for installed engineering tools, issue tracking, and domain documentation.

## Deliverable

Return the required local configuration or documentation mapping existing tools to actual project conventions.

Done when: configured consumers resolve their tracker, labels, and document locations without conflicting definitions.

Stop and report when: a required tool or tracker capability cannot be discovered; identify the blocked action and continue independent work.

## Inputs

Repository instructions, existing tracker, installed tools, domain documents, requested setup scope.

## Decision rules

- Only configure integration points consumed by tools that actually exist.
- A remote host does not prove issue tracking is enabled or authenticated.
- Map existing label roles before proposing new names to avoid parallel vocabularies.
- Choose multiple context roots only when independent domains justify them, not from package count alone.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Discover runtime and repository conventions, reconcile existing settings, then write the smallest required integration and check its actual references or available validation command.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
