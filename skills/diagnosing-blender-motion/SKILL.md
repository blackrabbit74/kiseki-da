---
name: diagnosing-blender-motion
description: "Diagnose character rig, pose, retargeting, and contact problems using structured Blender state and visual evidence. Use when an imported or animated character appears twisted, mirrored, offset, or foot-sliding; not for judging motion from screenshots alone or unrelated modeling work."
---

# Diagnosing Blender Motion

## Purpose

Diagnose character rig, pose, retargeting, and contact problems using structured Blender state and visual evidence.

## Deliverable

Return frame-specific findings with objects, bones, coordinates, likely causes, and repair evidence if requested.

Done when: the clean baseline and sampled motion explain each confirmed failure.

Stop and report when: the scene or Blender runtime is unavailable for extracting required transforms; identify the blocked action and continue independent work.

## Inputs

Scene file, expected axes and pose, animation range, ground plane, repair scope.

## Decision rules

- Separate character geometry from proxies before interpreting bounds.
- Compare local, armature, and world transforms; apparent mirroring can arise from axis conventions or negative scale.
- Check planted-foot world positions across frames, not only clearance in one image.
- Separate bone swing from roll when diagnosing twist damage.

## Required procedure

1. Inspect the supplied scope, existing conventions, and relevant evidence.
2. Inventory scene and rest pose, sample contacts and extremes, then corroborate measured failures with renders. Preserve originals while testing repairs.
3. Return the result with observed verification, remaining uncertainty, and the next blocked dependency if any.

## Constraints (set by: operator)

Preserve the user’s scope and existing authorization. Verify version-sensitive interfaces against the actual environment when executing.

## Model notes

No model-specific adjustment.
