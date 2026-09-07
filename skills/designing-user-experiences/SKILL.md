---
name: designing-user-experiences
description: "Defines an experience through user goals, journeys, information, states, feedback, and interaction decisions. Use for a UX concept or JRPG player flow connecting exploration, combat, and progression; visual production requires its own requested scope."
---

# Designing User Experiences

## Purpose

Specify what the user or player does, understands, and experiences at each meaningful transition.

## Deliverable

Return a representative journey, surfaces or game situations, available actions, information, state transitions, feedback, recovery, and open experience decisions.

Done when: each stated need is served by a reachable interaction and each important action has understandable feedback and consequence.

Stop and report when: the target platform or core interaction goal is unknown and changes the design; identify the decision it blocks.

## Inputs

Use product or game concept, audience, platform, input method, existing design conventions, and experience constraints.

## Decision rules

- If an interface style is already established, specify the needed behavioral change rather than replacing its identity.
- If an action can fail, include the visible state and recovery path.
- If designing a JRPG loop, read [player experience](references/jrpg-player-experience.md).
- If accessibility changes an interaction, consider input alternatives and readable feedback within the stated platform.

## Required procedure

1. Describe one realistic session from intention to outcome.
2. Map needs to situations, actions, state changes, and feedback.
3. Resolve missing paths and separate visual presentation choices from behavioral requirements.

## Constraints (set by: operator)

- Do not treat a visual mockup as proof of usability or enjoyable play. Instead, name the observation or playtest still needed.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
