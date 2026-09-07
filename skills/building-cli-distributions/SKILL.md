---
name: building-cli-distributions
description: "Builds command-line tools or application installers with usable commands, packaging metadata, runtime dependencies, and distribution checks. Use for a distributable CLI or installer; not for forcing a particular language, architecture, or packager on an existing project."
---

# Building Cli Distributions

## Purpose

Deliver a tool that works outside the development environment.

## Deliverable

Return implementation or installer, usage guidance, build recipe, and tested distribution properties.

Done when: target installation and representative commands are checked, with unsupported platforms named.

Stop and report when: the target platform or signing access is unavailable; deliver build artifacts and explicit unverified checks. Continue independent work and identify the blocked action.

## Inputs

Commands or app, target platforms, runtime, metadata, output formats, and existing packaging.

## Decision rules

- Choose CLI complexity from actual subcommand and extension needs.
- Separate machine output on stdout from diagnostics; provide meaningful exit codes and help.
- Trim packaged files only after checking runtime metadata, plugins, and dynamic dependencies.

## Required procedure

1. Inspect existing commands and target runtime requirements.
2. Implement command behavior and packaging with current tool documentation.
3. Test clean installation, launch, help, failure exits, and upgrade or uninstall where applicable.

## Constraints (set by: operator)

Do not default to 32-bit for size or strip runtime dependencies based only on filenames. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
