---
name: auditing-and-remediating-security
description: "Reviews a scoped application or code change for concrete security weaknesses and implements requested remediation with evidence. Use for security audits or hardening work; not for declaring a system secure from a checklist or expanding into unauthorized testing."
---

# Auditing And Remediating Security

## Purpose

Find and repair exploitable weaknesses within the requested boundary.

## Deliverable

Return prioritized findings, affected paths, exploitation preconditions, fixes, and validation limits.

Done when: findings have concrete evidence and requested fixes are checked against their attack conditions.

Stop and report when: missing access or authorization prevents a specific security test. Continue independent work and identify the blocked action.

## Inputs

Scope, code, deployment context, trust boundaries, and available security tooling.

## Decision rules

- Trace untrusted input to sensitive effects; validation does not replace authorization.
- Distinguish exposed secrets from references to secret storage and redact evidence.
- Verify current advisories and applicability before claiming a dependency is vulnerable.

## Required procedure

1. Map sensitive operations and relevant entry points.
2. Inspect controls and validate suspected issues with bounded tests.
3. Implement scoped repairs and check the original failure conditions.

## Constraints (set by: operator)

Do not weaken security controls to make tests pass or claim exhaustive protection. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
