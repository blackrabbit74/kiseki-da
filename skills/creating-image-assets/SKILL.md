---
name: creating-image-assets
description: "Creates or edits illustrations, raster images, or icon assets from a concrete visual brief and references, validating composition and delivery constraints. Use for visual asset production; not for interface layout, scientific plots, or replacing an established vector icon system unnecessarily."
---

# Creating Image Assets

## Purpose

Produce assets that fit their actual placement.

## Deliverable

Return the image assets with dimensions, background treatment, and variants requested.

Done when: output is inspected against composition, legibility, and format requirements.

Stop and report when: the required image tool or reference is unavailable; deliver a precise visual brief. Continue independent work and identify the blocked action.

## Inputs

Subject, use case, references, style, dimensions, transparency, and existing assets.

## Decision rules

- Choose raster generation for pictorial visuals and preserve vector systems when editability matters.
- Inspect reference images before editing and state which features must remain stable.
- Check transparent assets against light and dark backgrounds; distinguish true alpha from a painted checkerboard.

## Required procedure

1. Translate use and references into composition constraints.
2. Discover available generation or editing tools and create the asset.
3. Inspect the actual result and correct material mismatches.

## Constraints (set by: operator)

Do not invent empirical model rankings or impose a personal palette. Preserve the user's scope and existing authorization.

## Model notes

No model-specific adjustment.
