---
name: empirical-benchmark-harness
description: Validate empirical-analysis agents against small known-answer benchmark tasks such as bad controls, weak IV, RDD, staggered DiD, matching imbalance, event studies, DML, and replication setup. Use when testing whether a workflow or skill produces methodologically sound empirical research outputs.
user-invocable: true
license: Apache-2.0
---

# Empirical Benchmark Harness

Source adaptation: BioRouter-original benchmark design inspired by Auto-Empirical Research Skills eval/benchmark harness, rewritten under Apache-2.0.

Use this skill to test an agent or workflow before trusting it on user data.

## Benchmark Pattern

Each benchmark should have:

- A small synthetic or public dataset.
- A known-answer estimand.
- A tempting wrong answer.
- Machine-checkable output requirements.
- A human-readable rubric for design reasoning.

## Core Scenarios

| Scenario | Correct behavior | Common failure |
|---|---|---|
| Bad control | Refuse mediator adjustment for total effect | Controls away the causal path |
| Weak IV | Report weak-IV robust inference | Headlines naive 2SLS |
| RDD | Use local linear/bandwidth sensitivity | Uses global polynomial or side means |
| Staggered DiD | Use cohort/time robust estimator | Plain TWFE as primary |
| Matching | Surface imbalance and overlap | Reports naive ATT only |
| Event study | Check pre-trends and dynamics | Treats one plot as proof |
| DML | Cross-fit nuisance models | Trains and estimates on same folds |
| Replication | Clean-run package and logs | Ships scripts that only work locally |

## Rubric

Score:

- `0`: wrong estimand or fabricated evidence.
- `1`: right tool family but missing critical diagnostics.
- `2`: correct method and diagnostics, incomplete communication.
- `3`: correct method, diagnostics, caveats, and reproducible output.

Fail any workflow that scores `0` on identification, citation reality, or reproducibility.
