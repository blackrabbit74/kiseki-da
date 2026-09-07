---
name: producing-document-exports
description: "Creates or converts documents and PDFs while preserving content, hierarchy, links, and pagination in the requested format. Use when document layout or export fidelity matters; not for merely rewriting prose or silently dropping unsupported content to make conversion succeed."
---

# Producing Document Exports

## Purpose

Deliver a faithful, readable document export.

## Deliverable

Return the requested document, editable source when relevant, and rendering limitations.

Done when: text, images, tables, links, and page breaks are visually checked.

Stop and report when: a missing asset or renderer prevents a faithful part of the export. Continue independent work and identify the blocked action.

## Inputs

Source files, target format, page size, template, and content constraints.

## Decision rules

- Separate content conversion from cosmetic changes; preserve code and tables during troubleshooting.
- Use the available format-specific tooling and inspect actual output rather than trusting exit status.
- When fonts or remote assets fail, identify the substitution and preserve meaning.

## Required procedure

1. Inventory source structure and select the conversion route.
2. Generate the document with appropriate styles and pagination.
3. Render pages, inspect clipping and missing elements, and verify text extraction where required.

## Constraints (set by: operator)

Do not remove substantive content to work around a conversion error. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
