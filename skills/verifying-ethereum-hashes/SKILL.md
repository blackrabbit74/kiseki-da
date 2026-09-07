---
name: verifying-ethereum-hashes
description: "Implement and verify Ethereum hashing and identifier helpers with correct byte encoding and algorithm selection. Use when JavaScript or TypeScript selectors, topics, storage slots, or typed-data hashes are incorrect; not for signing transactions or assuming any installed SHA3 implementation is Ethereum-compatible."
---

# Verifying Ethereum Hashes

## Purpose

Implement and verify Ethereum hashing and identifier helpers with correct byte encoding and algorithm selection.

## Deliverable

Return corrected helpers with encoding explanations and known-vector regression evidence.

Done when: the target identifiers match independently sourced vectors for the actual encoding contract.

Stop and report when: a compatible hashing implementation cannot be discovered in the runtime; identify the blocked action and continue independent work.

## Inputs

Existing dependencies, input types, expected identifiers, chain/domain context, runtime version.

## Decision rules

- Ethereum Keccak-256 and NIST SHA3-256 differ despite similar names.
- Text containing hexadecimal digits is not necessarily the bytes those digits encode.
- Packed ABI encoding can be ambiguous for multiple dynamic fields; choose the protocol-required encoding.
- Function selectors use canonical signatures; argument names and aliases can change a mistakenly constructed preimage.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Discover the installed crypto library and current API, inspect exact preimage bytes, and compare empty, text, ABI, and protocol-specific vectors without using wallet secrets.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
