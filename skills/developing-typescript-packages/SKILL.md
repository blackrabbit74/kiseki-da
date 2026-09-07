---
name: developing-typescript-packages
description: "Implement and verify TypeScript or Node library boundaries, runtime behavior, and package distribution contracts. Use when a TypeScript SDK, package export, or Node module needs development or repair; not for automatic registry publication or replacing the monorepo toolchain."
---

# Developing Typescript Packages

## Purpose

Implement and verify TypeScript or Node library boundaries, runtime behavior, and package distribution contracts.

## Deliverable

Return the package change with type checks, runtime consumer tests, and packed-artifact evidence where distribution changes.

Done when: supported consumers can import the built package and declarations match runtime exports.

Stop and report when: the required consumer runtime is unavailable for a compatibility claim; identify the blocked action and continue independent work.

## Inputs

Node/TypeScript versions, package exports, module modes, target runtimes, public API contract.

## Decision rules

- TypeScript types disappear at runtime; validate external values where correctness depends on their shape.
- ESM and CommonJS can resolve different exports and declarations; test supported modes explicitly.
- Workspace source imports can hide missing files in the published archive.
- Browser or worker compatibility requires removing Node-only assumptions, not just selecting a type library.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Trace public entrypoints, implement the change, and exercise real consumers against built or packed output with relevant module-resolution settings.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
