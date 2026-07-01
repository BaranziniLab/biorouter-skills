---
name: machine-learning-model-explainability-shap
description: Explain predictive biomedical models with SHAP and related feature-attribution methods while checking leakage, correlated features, background data choice, and causal overinterpretation. Use when interpreting model predictions or communicating feature importance.
tool_type: python
primary_tool: shap
user-invocable: false
license: Apache-2.0
---

# SHAP and Model Explainability

Use SHAP to explain model predictions, not to prove biological causality.

## Gate Checks

- Model is already validated on held-out data.
- Background/reference dataset matches the target population.
- Feature leakage and target proxies have been checked.
- Highly correlated features are interpreted as groups when needed.
- Protected or clinical variables are handled responsibly.

## Workflow

1. Identify model type and choose compatible explainer.
2. Select representative background data.
3. Compute global and local explanations.
4. Compare attribution stability across folds or bootstraps.
5. Check whether top features are artifacts, batch variables, or proxies.
6. Report what SHAP can and cannot support.

## Output Rules

- Say "the model used this feature" rather than "this feature causes the outcome."
- Include uncertainty or stability for feature rankings when possible.
- Pair local explanations with the actual prediction and baseline.

## Related Skills

- `machine-learning/causal-ml-dml`
- `machine-learning/model-evaluation`
- `claim-evidence-integrity`
