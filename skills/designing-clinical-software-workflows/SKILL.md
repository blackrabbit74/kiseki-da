---
name: designing-clinical-software-workflows
description: "Design or implement clinical software workflows with explicit patient identity, data integrity, and safety validation. Use for EHR encounters, medication interfaces, results handling, or clinical decision-support integration; it does not provide patient-specific diagnosis or establish deployment safety from aggregate test scores."
---

# Designing Clinical Software Workflows

## Purpose

Design or implement clinical software workflows with explicit patient identity, data integrity, and safety validation.

## Deliverable

Return workflow states or implementation, clinical data contracts, failure handling, traceable safety cases, and validation results.

Done when: critical paths and failures have observable expected behavior tied to current approved clinical requirements.

Stop and report when: an unresolved clinical rule or safety-critical failure prevents the dependent feature’s release; continue isolated design and nondependent validation. Continue independent work and identify the specific blocked action.

## Inputs

Users and care setting, jurisdiction, clinical requirements, encounter states, terminology sources, integration formats, and test fixtures.

## Decision rules

- Keep patient identity, allergies, units, and relevant context visible at consequential actions.
- Distinguish draft, signed, locked, and amended records; preserve concurrent-edit and audit behavior.
- A high overall pass rate cannot excuse a failed critical safety case or missing tests.

## Required procedure

1. Map clinical actions, handoffs, failure consequences, and accountable decision points.
2. Verify clinical rules and applicable standards against current authoritative sources with date and jurisdiction.
3. Implement or specify the flow and test identity mixups, missing inputs, interaction failures, malformed integrations, and recovery using synthetic data.

## Constraints (set by: operator)

Do not invent dosing thresholds, treat automation as clinician authorization, or alter real patient records merely to test a workflow. Preserve the user’s scope and existing authorization.

## Model notes

No model-specific adjustment.
