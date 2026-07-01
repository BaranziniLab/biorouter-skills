---
name: arbor-optimization
description: Run evaluator-driven hypothesis trees for improving research artifacts, prompts, analyses, and designs. Use when a task needs branch-and-prune exploration, rubric scoring, iterative refinement, or explicit comparison of competing scientific/workflow alternatives.
user-invocable: true
license: Apache-2.0
---

# Arbor Optimization

Source adaptation: BioRouter-original synthesis inspired by Scientific Agent Skills tree-optimization patterns, rewritten under Apache-2.0. This is a native BioRouter iterative-improvement workflow.

## When to Use

Use this skill when a single-shot answer is not enough and the user wants structured exploration: competing hypotheses, analysis plans, designs, prompts, figures, abstracts, protocols, or implementation options.

## Define the Tree

Before branching, define:

- Objective and non-negotiable constraints.
- Evaluation rubric with 3-7 criteria.
- Evidence sources or tests available.
- Maximum branch count and stopping rule.
- What counts as a failed branch.

## Branching Pattern

1. Create 3-5 materially different candidate branches.
2. For each branch, state the core idea, assumptions, expected upside, and failure mode.
3. Score branches against the rubric.
4. Prune weak branches with a short reason.
5. Refine the strongest branch once, incorporating the best elements from competitors.
6. Produce a final recommendation with the rejected alternatives preserved in a compact comparison.

## BioRouter Routes

- Use `empirical-benchmark-harness` when the branch can be tested against known-answer empirical cases.
- Use `replication-package-audit` when the winning branch creates a runnable analysis.
- Use `claim-evidence-integrity` for manuscript or report branches.
- Use `scientific-visual-communication` for figure/poster/slide alternatives.
- Use domain skills or BRXT extensions before scoring branches that depend on platform data.

## Quality Gates

Do not call a branch "best" unless:

1. The rubric is visible.
2. Evidence or test results are tied to each score.
3. Tradeoffs are explicit.
4. The final answer names what would change the recommendation.
5. The user can rerun or audit the decision.

## Response Shape

Return:

- Objective.
- Rubric.
- Branch table.
- Pruned branches.
- Refined winner.
- Verification still needed.
