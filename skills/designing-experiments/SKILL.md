---
name: designing-experiments
description: "Designs falsifiable experiments with competing explanations, measurements, decision rules, and stopping conditions. Use when deciding how to test a business hypothesis, product assumption, research question, or player-experience claim before collecting evidence."
---

# Designing Experiments

## Purpose

Make the next test capable of changing a decision rather than merely confirming a preferred story.

## Deliverable

Return a protocol with question, competing hypotheses, population or units, intervention, comparator, measures, confounders, decision rules, and stopping conditions.

Done when: the protocol specifies observations that support, contradict, or leave each hypothesis unresolved before data collection.

Stop and report when: the proposed design cannot distinguish the hypotheses with available measurements; explain the limitation and revise the test.

## Inputs

Use the decision, current evidence, accessible participants or data, resource limits, and feasible interventions.

## Decision rules

- If behavior is the claim, measure behavior rather than substituting stated preference.
- If sample size or allocation limits inference, identify the limit before interpreting results.
- If testing a JRPG experience, read [the playtest protocol guide](references/playtest-protocol.md).
- If outcomes are already known, distinguish exploratory analysis from a prospectively specified test.

## Required procedure

1. Name competing explanations and their differing predictions.
2. Choose measures and controls that separate those predictions.
3. Specify analysis, decision thresholds, and stopping conditions before the run.

## Constraints (set by: operator)

- Do not claim an experiment ran or participants responded without observations. Instead, deliver the protocol or label simulation as simulation.

## Model notes

- Claude: Identify targets by their decision criteria without redundant private labels.
- GPT: State boundaries once and honor the user’s current scope and choices.
