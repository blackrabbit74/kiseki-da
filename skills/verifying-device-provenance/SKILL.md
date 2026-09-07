---
name: verifying-device-provenance
description: "Verify device provenance records for sequence gaps, hash-chain integrity, and available authenticity evidence. Use for IoT witness-chain review or fleet audit records; a device health check or a tool’s success flag alone does not prove provenance."
---

# Verifying Device Provenance

## Purpose

Verify device provenance records for sequence gaps, hash-chain integrity, and available authenticity evidence.

## Deliverable

Return device identity, checked epoch range, record count, gaps, hash and signature evidence, and a verified/failed/inconclusive result.

Done when: the result states exactly which records and trust anchors were checked and preserves unresolved gaps.

Stop and report when: required records, hash material, or a trusted key are unavailable; mark the affected assurance claim inconclusive. Continue independent work and identify the specific blocked action.

## Inputs

Device identity, witness entries, epoch order, hash algorithm and encoding, expected range, and trusted verification keys if applicable.

## Decision rules

- An empty chain is no evidence of history even when a CLI reports success.
- Missing hash fields are unverified data, not a passed comparison.
- Distinguish internal chain consistency from device authenticity; verify signatures against an independently trusted key.
- A numeric integrity score cannot replace the actual gap and failure evidence.

## Required procedure

1. Discover the device or export interface and retrieve the intended record range.
2. Check order, duplicate epochs, gaps, predecessor hashes, and supported authentication evidence.
3. Record concise findings with source references; preserve original entries and verify any authorized audit-record write.

## Constraints (set by: operator)

Do not repair, erase, or re-sign history as part of verification or install an unreviewed package merely to obtain a score. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
