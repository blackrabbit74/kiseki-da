---
name: building-service-connectors
description: "Implements API or MCP integrations using the host repository\u2019s current connector patterns, including configuration, mapping, discovery, and tests. Use when adding a service integration; not for stopping at a generic HTTP client or inventing a parallel integration architecture."
---

# Building Service Connectors

## Purpose

Make the new integration behave like a native repository component.

## Deliverable

Return connector code, registration, configuration guidance, and integration checks.

Done when: the connector is discoverable and handles its supported operations and failure modes.

Stop and report when: service access prevents live verification; complete local implementation and fixtures. Continue independent work and identify the blocked action.

## Inputs

Target service, required operations, current connectors, API documentation, and auth model.

## Decision rules

- Compare existing connectors and identify the current pattern rather than copying an obsolete example.
- Retry only operations whose semantics make retries safe; handle pagination and rate limits.
- Separate transport errors from domain mapping errors and avoid leaking credentials.

## Required procedure

1. Inspect repository integration seams and current official service schemas.
2. Implement required operations plus registration and configuration.
3. Test mapping, auth failures, pagination, and discovery; distinguish mocks from live checks.

## Constraints (set by: operator)

Do not invent credentials, endpoints, or supported operations. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
