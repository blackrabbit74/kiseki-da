---
name: developing-angular-features
description: "Implement and verify Angular components, services, forms, and routes using the project\u2019s supported framework conventions. Use when an Angular feature or framework-specific defect needs code changes; not for generic frontend work or automatically upgrading Angular."
---

# Developing Angular Features

## Purpose

Implement and verify Angular components, services, forms, and routes using the project’s supported framework conventions.

## Deliverable

Return the requested change with template/build checks and focused interaction evidence.

Done when: template typing and relevant form, route, or asynchronous behavior pass on the target version.

Stop and report when: the required Angular toolchain is unavailable for a build; identify the blocked action and continue independent work.

## Inputs

Angular version, project configuration, existing forms and state patterns, affected interactions.

## Decision rules

- Match the project’s supported forms strategy; new signal APIs are not assumed available.
- Use derived reactive state for derivations and effects for external side effects to avoid update loops.
- Injector scope changes service lifetime and state sharing; verify the intended provider boundary.
- Server rendering cannot use browser globals during server execution.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Trace the component and dependency boundaries, implement the behavior, then build templates and test teardown, invalid forms, and navigation where relevant.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
