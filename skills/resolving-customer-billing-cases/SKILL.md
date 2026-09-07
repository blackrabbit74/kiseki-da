---
name: resolving-customer-billing-cases
description: "Investigate customer billing, subscription, invoice, or contract-state problems and prepare or apply authorized remedies. Use for duplicate charges, failed renewals, cancellation, or seat confusion; generic payment API development and permission to issue refunds are separate concerns."
---

# Resolving Customer Billing Cases

## Purpose

Investigate customer billing, subscription, invoice, or contract-state problems and prepare or apply authorized remedies.

## Deliverable

Return verified customer and transaction identities, classified issue, remedy, financial effect, and actual post-action state or ready-to-apply draft.

Done when: the remedy addresses the specific billing state and affected amount without changing unrelated subscriptions or entitlements.

Stop and report when: identity, contract interpretation, authorization, or an uncertain transaction result prevents the proposed mutation. Continue independent work and identify the specific blocked action.

## Inputs

Customer or transaction identifier, subscription and invoice records, contract terms, relevant support history, and authorized actions.

## Decision rules

- Multiple subscriptions may represent legitimate seats rather than duplicates.
- Check renewal timing, annual commitments, proration, tax, and entitlement effects before changing a plan.
- A refund and cancellation are distinct operations; verify each separately and inspect state before retrying.

## Required procedure

1. Discover the billing interface and reconcile customer, invoice, payment, and subscription records.
2. Classify the problem and verify applicable current terms and jurisdiction-specific requirements.
3. Prepare or execute the authorized remedy, read back its state, and draft any customer follow-up separately.

## Constraints (set by: operator)

Do not expose card details or credentials; reading a complaint does not authorize refunds, contract changes, or sending messages. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
