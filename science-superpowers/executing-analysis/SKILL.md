---
name: executing-analysis
description: "Use when you have a pre-registered analysis plan to execute inline in this session with review checkpoints, on a platform without subagents"
license: Apache-2.0 AND MIT
user-invocable: true
metadata:
  version: "1.0.0"
  origin: "adapted"
  upstream: "K-Dense-AI/science-superpowers/skills/executing-analysis@0374bdf82c2372bdf1667e3c762146c3a29215f5"
  upstream_licence: "MIT"
---

<!-- Adapted for Biorouter from K-Dense-AI/science-superpowers (skills/executing-analysis, commit 0374bdf82c23), MIT. Changes: dispatcher and subagent-orchestration skills dropped; references to them and Claude Code tool names replaced with Biorouter equivalents. See LICENSE-UPSTREAM. -->

# Executing the Analysis

## Overview

Load the pre-registered plan, review it critically, execute all steps exactly as registered, report when complete.

**Announce at start:** "I'm using the executing-analysis skill to run this analysis."

**Note:** the protocol-compliance and rigor reviews catch more when run by fresh agents. If subagents are available (Biorouter's `subagent` tool), run each step's reviews in a fresh subagent, as `requesting-red-team-review` describes.

## Prerequisite

The plan MUST be pre-registered and frozen (`preregistering-analysis`) and the workspace set up (`setting-up-reproducible-analysis`). If either is missing, stop and do it first. Executing before freezing turns the analysis exploratory.

## The Process

### Step 1: Load and Review

1. Read the analysis plan and the frozen pre-registration.
2. Review critically — any concern about the design, the decision rule, or feasibility?
3. If concerns: raise them with your human partner before starting. A change to the registered analysis is a documented deviation and renders that part exploratory.
4. If no concerns: write a checklist of all steps (a todo list if your tools have one) and proceed.

### Step 2: Execute Steps

For each step:
1. Mark in_progress.
2. For nontrivial estimators: validate the pipeline on known/simulated data first.
3. Run the step exactly as registered. Keep the seed. Read immutable raw / named derived; write a new artifact.
4. Validate the output (shape, ranges, counts) — nothing changes silently.
5. Apply the registered decision rule as written; do not re-decide it after seeing the number.
6. Use `verifying-results-before-claiming` before marking done.
7. Commit. Mark completed.

### Checkpoints

After each natural group of steps (e.g., data prep, then primary model), pause and report results to your human partner before continuing. Keep confirmatory and exploratory results clearly separated in every report.

### Step 3: Complete

After all steps complete and verified:
- Use `requesting-red-team-review` on the whole result.
- Then `reporting-and-archiving-findings`.

## When to Stop and Ask

**STOP immediately when:**
- A result is surprising, impossible, or contradicts a sanity check → use `investigating-anomalous-results` (do NOT quietly drop data or tweak parameters)
- The plan requires deviating from the pre-registration to proceed
- A validation fails repeatedly
- An instruction is unclear

**Ask rather than guess.** A guess that changes the analysis silently destroys the result's credibility.

## Remember

- Pre-registration frozen before execution
- Validate pipelines on known data
- Run steps exactly as registered; never silently deviate
- Label anything unregistered as exploratory
- Don't skip validation or verification
- Stop on anomalies; investigate by root cause

## Integration

**Required workflow skills:**
- **setting-up-reproducible-analysis** — run first
- **preregistering-analysis** — frozen before execution
- **investigating-anomalous-results** — on surprising results
- **verifying-results-before-claiming** — before any completion claim
- **reporting-and-archiving-findings** — after all steps complete
