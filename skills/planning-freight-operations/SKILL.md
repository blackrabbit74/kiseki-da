---
name: planning-freight-operations
description: "Compare carriers and prepare shipment allocation or exception responses using lane-level cost, capacity, and service evidence. Use for freight sourcing, routing guides, late pickups, or carrier performance; it does not book transport or commit commercial terms without authorization."
---

# Planning Freight Operations

## Purpose

Compare carriers and prepare shipment allocation or exception responses using lane-level cost, capacity, and service evidence.

## Deliverable

Return a shipment or lane plan, comparable total costs, carrier evidence, primary and fallback options, and unresolved execution conditions.

Done when: the plan accounts for timing, equipment, service risk, and capacity rather than quoted linehaul price alone.

Stop and report when: a required carrier qualification, capacity commitment, or shipment constraint cannot be verified; hold that award or booking. Continue independent work and identify the specific blocked action.

## Inputs

Origin and destination, cargo and handling needs, windows, volume, bids, contracts, carrier performance, and existing bookings.

## Decision rules

- Compare linehaul, fuel tables, minimums, and accessorials on the same lane and assumptions.
- Separate pickup reliability, delivery reliability, tender acceptance, and claims severity.
- A backup carrier must have viable capacity and authority, not merely a low historical rate.

## Required procedure

1. Reconcile shipment constraints and current status.
2. Verify current applicable carrier authority, insurance, restrictions, and quote validity using jurisdiction-relevant sources.
3. Build primary and contingency choices with total cost and exception triggers; execute only authorized tenders and verify confirmations.

## Constraints (set by: operator)

Do not invent standard prices or fixed allocation ratios, impersonate a licensed operator, or contact carriers without explicit authorization. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
