---
name: designing-agent-payment-controls
description: "Implement or assess agent payment flows with exact amount handling, explicit spending limits, and verifiable transaction state. Use for paid API access or machine-initiated payment integration; a payment challenge or available wallet balance is not authorization to spend."
---

# Designing Agent Payment Controls

## Purpose

Implement or assess agent payment flows with exact amount handling, explicit spending limits, and verifiable transaction state.

## Deliverable

Return the payment flow or implementation, amount and currency contract, budget controls, recipient checks, retry semantics, and test or transaction evidence.

Done when: amounts, recipients, limits, and final states are verified without silent overpayment or duplicate settlement.

Stop and report when: authorization, recipient identity, available budget, or settlement state is unresolved; hold the payment and continue independent nonspending design. Continue independent work and identify the specific blocked action.

## Inputs

Buyer or seller role, payment protocol, asset and network, decimal precision, fees, recipient policy, explicit authorization, and current SDK capabilities.

## Decision rules

- Use integer minor units or exact decimals with explicit rounding and asset precision.
- Enforce cumulative limits atomically across concurrent calls, including fees and retries.
- Treat a timeout as uncertain settlement; reconcile before retrying with a stable idempotency identity.

## Required procedure

1. Verify current protocol, network, SDK, and applicable legal requirements from authoritative sources for the execution date and jurisdiction.
2. Implement price validation, recipient constraints, authorization checks, and bounded retries with protected key handling.
3. Test declines, malformed challenges, over-budget requests, concurrent spending, and duplicate callbacks in a nonspending environment; verify any authorized live result.

## Constraints (set by: operator)

Never expose private keys or claim non-custodial means risk-free. Block actions whose total charge, including fees and concurrent reservations, would exceed the hard spending limit. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
