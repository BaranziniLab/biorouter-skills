---
name: causal-heterogeneity-policy-learning
description: Estimate how a treatment effect varies across people, places or time and turn that into a targeting policy, with double machine learning, causal forests, meta-learners (S, T, X, R, DR), calibration and RATE tests for heterogeneity, policy trees and off-policy evaluation, conformal intervals for individual effects, and subgroup and fairness checks. Use for CATE, heterogeneous treatment effects, uplift, who benefits most, treatment rules, or personalised policies, once the design identifies an average effect.
user-invocable: true
license: Apache-2.0
metadata:
  version: "1.1.0"
  origin: native
  upstream: "none (native rewrite; folds in the Biorouter-original bio-skills machine-learning/causal-ml-dml component)"
---

# Causal Heterogeneity and Policy Learning

Average effects answer "does it work"; this skill answers "for whom, and what should we do
about it". It assumes the design already identifies a causal effect. If that has not been
checked, run `causal-identification-gates` first: no estimator below repairs confounding, and
flexible models make unidentified effects look precise.

This skill carries the full method behind the bio `machine-learning` bundle's `causal-ml-dml`
component, whose gate checks and reporting rules are included below. Use that component for its
omics and biomarker context, and this skill for the estimation and policy steps.

## Name the estimand

| Estimand | Question | Typical output |
| --- | --- | --- |
| ATE or ATT | Average effect in the population or the treated | One number with an interval |
| CATE, tau(x) | Effect for units with covariates x | A function; summarised, never shown raw |
| GATE | Effect in pre-specified groups (age bands, sites, genotypes) | A table of group effects with intervals |
| Policy value | Average outcome if treatment followed rule pi(x) | Value of the rule against treat-all, treat-none and the current practice |

Pre-specify the groups and the candidate effect modifiers. A search over many subgroups with
no plan will find "heterogeneity" in noise.

## Choose the estimator

| Situation | Estimator | Software |
| --- | --- | --- |
| Many confounders, effect of a binary or continuous treatment, interest in ATE and a few modifiers | Double ML (partially linear or interactive model) with cross-fitting | Python `doubleml`, `econml.dml.LinearDML`; R `DoubleML` |
| Flexible CATE with honest intervals and built-in tests | Causal forest (generalised random forest) | R `grf::causal_forest`; Python `econml.dml.CausalForestDML` |
| CATE from any ML learner | Meta-learners: T (separate models), S (treatment as a feature), X (good with imbalanced arms), R (orthogonalised loss), DR (doubly robust pseudo-outcome) | `econml.metalearners`, `econml.dr.DRLearner`; R `grf`, `rlearner` |
| Instrumented or randomised-encouragement designs | IV forest or DML-IV | `grf::instrumental_forest`, `econml.iv` |
| Learn a treatment rule | Policy tree on doubly robust scores, or a DR policy learner | R `policytree`; `econml.policy.DRPolicyTree` |

Prefer orthogonalised estimators (DML, R-learner, DR-learner, causal forest): they are less
sensitive to errors in the nuisance models than plain S- or T-learners.

## Workflow

1. **Design gate.** Confirm identification with `causal-identification-gates`, and write the
   estimand, treatment, outcome, confounders and candidate modifiers. Separate confounders from
   mediators and colliders; never adjust for post-treatment variables.
2. **Split before fitting.** Use K-fold cross-fitting for every nuisance model (outcome model
   and propensity score), keeping units from one cluster (patient, site, family) in one fold.
3. **Fit and check nuisances.** Report out-of-fold performance of the outcome and propensity
   models. Poor nuisance fits mean noisy effects; a propensity model that predicts treatment
   almost perfectly means overlap is failing.
4. **Check overlap.** Plot propensity scores by arm. Trim or restrict to the region of common
   support (for example 0.05 to 0.95), and state that the estimand now covers that region only.
5. **Estimate the ATE first**, with an interval, and compare with simpler estimators
   (regression adjustment, inverse probability weighting). Large disagreement is a warning.
6. **Test whether heterogeneity exists** before describing it:
   - the calibration test of the forest (`grf::test_calibration`), where a significant
     "differential forest prediction" coefficient indicates real heterogeneity;
   - the best linear predictor test of the generic ML approach (Chernozhukov, Demirer, Duflo and
     Fernandez-Val), which regresses doubly robust scores on the predicted CATE;
   - the rank-weighted average treatment effect (RATE) with its TOC or Qini curve, estimated on
     held-out data (`grf::rank_average_treatment_effect`).
   If none of these finds heterogeneity, report the average effect and stop.
7. **Describe heterogeneity with groups, not points.** Report GATEs for pre-specified groups and
   for quantiles of the predicted CATE (sorted group average effects), each with doubly robust
   intervals. Show which covariates drive the predicted CATE with variable importance or a best
   linear projection (`grf::best_linear_projection`), described as association with the effect,
   not mechanism.
8. **Learn the policy on one split, evaluate it on another.** Fit a shallow policy tree (depth 2
   or 3 is readable) on doubly robust scores, then estimate its value on held-out data with
   intervals, against treat-all, treat-none and current practice. Include costs and capacity
   constraints if treatment is limited.
9. **Individual intervals, if needed.** Conformal methods for counterfactuals (weighted split
   conformal, Lei and Candes) give intervals for individual effects; they are wide, and that is
   the honest answer.
10. **Stability and fairness.** Re-estimate with different seeds and folds; report how often a
    unit is assigned to treatment. Check the policy's effect and assignment rates across
    protected groups, and whether any group is denied a treatment that benefits it on average.

## What not to claim

- Prediction accuracy of nuisance models is not evidence of causal validity.
- A CATE plot without intervals and without a heterogeneity test is decoration.
- "Patients like X benefit more" needs the GATE interval for X, not a single forest prediction.
- Do not rank individual patients for treatment from a research model without calibration,
  external validation, fairness review and clinical sign-off; route that to `clinical-ai-modeling`.

## Reporting checklist

Estimand and population, identification argument, confounders and modifiers (pre-specified or
not), estimator and nuisance learners with out-of-fold performance, cross-fitting scheme and
seeds, overlap handling, ATE with interval, heterogeneity test results, GATE table, policy value
with interval and comparators, stability and fairness results, software versions.

## Related skills

- `causal-identification-gates` (design validity) and `empirical-research-router` (staging).
- `econometrics-toolkit` for panel and event-study designs whose average effects come first.
- `scientific-machine-learning` for the nuisance learners and their evaluation.
- The bio `machine-learning` bundle (`causal-ml-dml`, `prediction-explanation`) for omics inputs,
  and `clinical-biostatistics` for effect measures in clinical studies.
- `empirical-benchmark-harness` to test the pipeline on a known-answer DML or CATE task.
