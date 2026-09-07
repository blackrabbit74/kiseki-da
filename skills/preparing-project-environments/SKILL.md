---
name: preparing-project-environments
description: "Prepare a reproducible project toolchain with compatible runtimes, native dependencies, and local services. Use for onboarding or environment-specific build failures; it does not replace an existing environment manager simply because another tool is available."
---

# Preparing Project Environments

## Purpose

Prepare a reproducible project toolchain with compatible runtimes, native dependencies, and local services.

## Deliverable

Return project-scoped configuration, setup instructions, resolved versions, and a verified activation or build result.

Done when: tools resolve inside the intended environment and setup repeats without hidden shell state.

Stop and report when: a required package or platform is unsupported; isolate that component and provide alternatives. Continue independent work and identify the specific blocked action.

## Inputs

Project manifests, lockfiles, OS and architecture, environment manager, native libraries, and service requirements.

## Decision rules

- Distinguish language packages from native system dependencies.
- Prefer the existing manager; use containers when OS isolation is necessary.
- Separate interactive shell customizations from non-interactive setup so CI can reproduce activation.

## Required procedure

1. Inspect version constraints and executable resolution.
2. Configure compatible project-scoped dependencies and idempotent setup.
3. Activate in a fresh process and verify the relevant build or connection.

## Constraints (set by: operator)

Do not put secrets in shared manifests or change system-wide defaults without task authorization. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
