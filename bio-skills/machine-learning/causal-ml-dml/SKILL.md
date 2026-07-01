---
name: machine-learning-causal-ml-dml
description: Estimate causal effects with double machine learning, orthogonal scores, cross-fitting, CATE/meta-learners, and uplift-style models while guarding against leakage and prediction-only claims. Use when the user wants machine learning for treatment effects rather than ordinary prediction.
tool_type: python
primary_tool: econml
user-invocable: false
license: Apache-2.0
---

# Causal ML and Double Machine Learning

Use this skill when ML models estimate treatment effects, heterogeneous effects, or policy-relevant contrasts.

## Gate Checks

- Estimand is defined before model choice.
- Treatment, outcome, confounders, instruments, and mediators are separated.
- Cross-fitting keeps nuisance models out of the final fold.
- The treatment has overlap across covariate space.
- Effect heterogeneity is validated, not only visualized.

## Workflow

1. Load `causal-identification-gates` for design validity.
2. Choose estimator: DML, DR learner, causal forest, T/X/S/R learner, uplift model, or targeted learner.
3. Split folds before nuisance fitting.
4. Fit outcome and treatment nuisance models.
5. Estimate ATE/ATT/CATE with uncertainty.
6. Check overlap, residuals, fold performance, and sensitivity.
7. Report allowed language based on identification quality.

## Reporting Rules

- Prediction accuracy does not prove causal validity.
- CATE plots require uncertainty and subgroup support.
- Do not rank patients for treatment without checking calibration, fairness, and clinical utility.

## Related Skills

- `causal-identification-gates`
- `clinical-biostatistics/effect-measures`
- `machine-learning/model-explainability-shap`
