---
name: managing-schedules-and-notifications
description: "Inspect, create, or update requested schedules and notifications using the actual host automation surface. Use for reminders, recurring checks, and overlapping or broken jobs; configuration presence alone does not prove execution, and ordinary work does not authorize a recurring task."
---

# Managing Schedules And Notifications

## Purpose

Inspect, create, or update requested schedules and notifications using the actual host automation surface.

## Deliverable

Return the job identity, timing and timezone, trigger behavior, notification intent, saved state, and verification or remaining setup requirements.

Done when: the saved configuration matches the request and configured, authenticated, and successfully executed states are distinguished.

Stop and report when: the host cannot express the schedule or lacks required access; provide the exact proposed job and identify the blocked creation step. Continue independent work and identify the specific blocked action.

## Inputs

Requested timing, timezone, repeat or event semantics, existing jobs, notification audience, and current host tools.

## Decision rules

- Inspect existing jobs before creating duplicates.
- Distinguish session-bound loops from persistent schedules and verify actual lifecycle behavior.
- Keep unchanged monitoring states quiet unless periodic updates were requested; account for timezone and daylight-saving transitions.

## Required procedure

1. Discover the native scheduling tool and inspect matching jobs and recent run evidence.
2. Create or update the requested job with concrete timing, action, and notification conditions.
3. Read back configuration and report the next scheduled occurrence when available; do not claim an unobserved run succeeded.

## Constraints (set by: operator)

Do not substitute shell cron for an unsupported native job silently or send notifications beyond the authorized recipients. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
