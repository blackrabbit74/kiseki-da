---
name: coordinating-project-progress
description: "Reconcile task, issue, and pull-request status into a coherent execution view with owners and next actions. Use for backlog coordination or cross-tracker project progress; individual bug diagnosis and automatic replication of every public issue are outside scope."
---

# Coordinating Project Progress

## Purpose

Reconcile task, issue, and pull-request status into a coherent execution view with owners and next actions.

## Deliverable

Return a reconciled work list with source links, owner, state, dependencies, stale claims, and authorized updates.

Done when: active items have a clear next action and conflicting tracker states are explained.

Stop and report when: a tracker is inaccessible or a material ownership conflict prevents its update. Continue independent work and identify the specific blocked action.

## Inputs

Relevant projects, tracker conventions, active issues and PRs, reviews, checks, milestones, and scope of permitted updates.

## Decision rules

- Identify each system’s role instead of assuming public and internal trackers share authority.
- Create internal tracking only when active ownership, scheduling, or coordination warrants it.
- An open PR may be waiting on review, checks, or a decision; do not call all inactivity stalled implementation.

## Required procedure

1. Read linked work and recent status evidence.
2. Reconcile duplicates and classify active, blocked, parked, and completed work using local conventions.
3. Apply authorized updates, verify returned states, and report unresolved dependencies.

## Constraints (set by: operator)

Discover available tracker tools; do not post messages or merge work merely to make a board appear complete. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
