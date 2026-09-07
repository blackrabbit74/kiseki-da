---
name: reviewing-transaction-execution
description: "Review code controlling swaps, liquidity, payments, or autonomous transaction execution for loss-producing failures. Use when funds or signing authority cross a trust boundary; not for investment recommendations or unrestricted live trading."
---

# Reviewing Transaction Execution

## Purpose

Review code controlling swaps, liquidity, payments, or autonomous transaction execution for loss-producing failures.

## Deliverable

Return findings with attack preconditions, loss mechanism, fixes, and reproducible local tests.

Done when: critical accounting and execution invariants have evidence and remaining gaps are explicit.

Stop and report when: validation requires unauthorized signing or live asset movement; identify the blocked action and continue independent work.

## Inputs

Execution code, asset semantics, spend policy, test environment, authority boundaries.

## Decision rules

- External metadata and messages are untrusted; text filtering is not an authorization boundary.
- Check reentrancy alongside donation, rounding, fee-on-transfer, and initial-liquidity behavior.
- Enforce spend limits atomically outside model judgment so concurrent orders reserve the same shared budget.
- Successful simulation does not guarantee success after state changes.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Map privileged entrypoints, external calls, and accounting state; exercise conservation, duplicate-execution, and maximum-loss invariants locally.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
