---
name: developing-perl-modules
description: "Implement and verify Perl modules and scripts with explicit context, encoding, and observable failure behavior. Use when Perl code or TAP tests need development or repair; not for rewriting unrelated code or mandating migration to a particular test library."
---

# Developing Perl Modules

## Purpose

Implement and verify Perl modules and scripts with explicit context, encoding, and observable failure behavior.

## Deliverable

Return the scoped Perl change with targeted TAP results and relevant input-boundary checks.

Done when: scalar/list context, malformed input, and process failures behave as specified.

Stop and report when: the required Perl interpreter or dependency set is unavailable; identify the blocked action and continue independent work.

## Inputs

Perl version, module paths, invocation context, encoding contract, existing test runner.

## Decision rules

- Scalar and list context can change a function’s result; test both only when the public contract supports both.
- Separate bytes from decoded characters at I/O boundaries; double decoding is not safer Unicode handling.
- Use list-form process invocation for argument separation and inspect process status instead of output alone.
- Localize modified globals in tests so order does not hide coupling.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Reproduce the issue under the declared interpreter, implement the smallest change, then run focused prove-compatible tests including undefined values and relevant encoding cases.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
