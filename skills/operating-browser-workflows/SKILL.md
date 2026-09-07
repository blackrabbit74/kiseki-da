---
name: operating-browser-workflows
description: "Completes user-directed website navigation, form entry, and browser workflows using observed page state and verified outcomes. Use when interacting with a web interface is required; not for bulk extraction or bypassing authentication and access restrictions."
---

# Operating Browser Workflows

## Purpose

Complete the intended browser workflow without duplicated submissions.

## Deliverable

Return the observed result or prepared form with exact blocked actions.

Done when: the resulting state is observed rather than inferred from a click.

Stop and report when: login, essential input, or authorization prevents the next action. Continue independent work and identify the blocked action.

## Inputs

Site, actions, supplied values, account context, and browser tools.

## Decision rules

- Discover supported APIs and use current element references.
- Refresh state after navigation or major DOM changes.
- Inspect state after uncertain submission before retrying.

## Required procedure

1. Identify the correct page and controls.
2. Enter values and inspect validation.
3. Perform authorized actions and verify the resulting record.

## Constraints (set by: operator)

Permission to fill a form does not by itself authorize messaging others. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
