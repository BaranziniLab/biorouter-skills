---
name: causal-identification-gates
description: Audit causal inference designs before estimation or interpretation, including randomized trials, observational adjustment, IV, RDD, DiD, staggered adoption, event studies, synthetic control, matching, DML, survival designs, and bad-control risks. Use when a user asks whether an empirical design supports causal language.
user-invocable: true
license: Apache-2.0
---

# Causal Identification Gates

Source adaptation: BioRouter-original synthesis from Auto-Empirical Research Skills causal-inference gates and Scientific Agent Skills statistics/tooling patterns, rewritten under Apache-2.0.

Use this skill before fitting or interpreting a causal model. The deliverable is a design gate: pass, pass with caveats, or fail with required remediation.

## Universal Gate

Require these items before causal language:

- Estimand: ATE, ATT, LATE, hazard ratio, risk difference, odds ratio, direct effect, mediated effect, or CATE.
- Assignment mechanism or source of variation.
- Timing: exposure before outcome, covariates before exposure, no post-treatment controls unless explicitly estimating a controlled direct effect.
- Comparison group and overlap/positivity.
- Inference unit and clustering level.
- Assumptions and falsification tests.

## Design-Specific Checks

| Design | Required checks |
|---|---|
| RCT | Randomization integrity, attrition, protocol deviations, pre-specified covariates |
| Observational regression | DAG/confounder rationale, no mediators/colliders, overlap, sensitivity to unmeasured confounding |
| IV | Relevance, exclusion restriction, independence, first-stage strength, weak-IV robust inference |
| RDD | Running variable integrity, bandwidth sensitivity, local linear fit, density test, covariate balance, placebo cutoffs |
| 2x2 DiD | Parallel trends support, no anticipation, stable composition, correct clustering |
| Staggered DiD | Avoid plain TWFE as primary when treatment effects vary; use cohort/time estimators and event-study diagnostics |
| Event study | Pre-trend visualization, joint pre-trend test, dynamic effects, clear omitted period |
| Synthetic control | Donor pool justification, pre-fit quality, placebo inference, donor weight inspection |
| Matching/weighting | Balance table, overlap, calipers/trim rules, estimand clarity, post-match inference |
| DML | Cross-fitting, nuisance model separation, orthogonal score, held-out diagnostics |
| Survival | Proportional hazards check, censoring assumptions, time-varying exposure handling |

## Red Flags

Block or downgrade causal claims when:

- A post-treatment variable is adjusted for without a direct-effect estimand.
- Treatment timing is staggered and plain TWFE is the only estimator.
- IV first-stage is weak and inference is ordinary 2SLS Wald-only.
- RDD uses global polynomials as the primary estimator.
- Matching reports treatment effects without balance or overlap.
- Machine learning predicts the outcome but never defines the causal contrast.

## Output Format

Return:

1. `Design`: chosen design and why.
2. `Estimand`: exact causal quantity.
3. `Gate`: pass, caveated pass, or fail.
4. `Required diagnostics`: concrete checks to run.
5. `Allowed language`: causal, quasi-causal, associational, or descriptive.
6. `Next action`: one command, model, plot, or data audit to perform.
