---
name: scientific-machine-learning
description: Design, train, evaluate and explain machine-learning models for scientific data with scikit-learn, PyTorch Lightning, Hugging Face Transformers, PyTorch Geometric and SHAP, with leakage-safe splits and honest evaluation. Use for classification, regression, clustering, dimensionality reduction, neural network training, fine-tuning a pretrained model, graph neural networks, hyperparameter tuning, model comparison, or explaining predictions with feature attributions.
user-invocable: true
license: Apache-2.0 AND MIT AND BSD-3-Clause
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/scikit-learn, skills/pytorch-lightning, skills/transformers, skills/torch-geometric, skills/shap)"
---

# Scientific Machine Learning

This skill keeps machine learning on scientific data honest: the split matches how the model
will be used, the baseline is beaten fairly, and explanations are not mistaken for mechanisms.
Framework detail lives in five guides under `references/`, adapted from K-Dense Scientific
Agent Skills (licences in `LICENSE-UPSTREAM`).

## Frame the task first

- **What decision will the prediction inform**, and what error costs more: a false positive or
  a false negative. This picks the metric (AUROC hides class imbalance; use AUPRC, balanced
  accuracy, calibration or a cost-weighted metric when it matters).
- **The independent unit.** If patients, donors, plates, sites or time periods produce several
  rows, the split must keep each unit wholly in train or test (`GroupKFold`,
  `StratifiedGroupKFold`, time-ordered splits). Row-level random splits on such data report
  accuracy the model will never have.
- **The deployment shift.** New hospital, new batch, new species, future time. Hold out data
  that differ the same way, and report that number as the headline.
- **A baseline.** Majority class or mean, a linear or logistic model with sensible features,
  and the method the field already uses. A deep model that does not beat a regularised linear
  model on held-out units is not a result.

## Choose the framework

| Data and goal | Use | Guide |
| --- | --- | --- |
| Tabular features, up to millions of rows; classification, regression, clustering, PCA, model selection | scikit-learn pipelines (gradient boosting via `HistGradientBoosting*`) | `references/scikit-learn.md` |
| Custom neural networks, images or signals, multi-GPU training, reproducible training loops | PyTorch Lightning (`LightningModule`, `Trainer`, `LightningDataModule`) | `references/pytorch-lightning.md` |
| Text, protein or other sequences with a pretrained model; zero-shot pipelines; fine-tuning | Hugging Face Transformers (pipelines, `AutoModel`, `Trainer`) | `references/transformers.md` |
| Molecules, interaction networks, meshes or any data that is a graph; node, edge or graph prediction | PyTorch Geometric | `references/torch-geometric.md` |
| Explaining any fitted model's predictions, global and local | SHAP explainers and plots | `references/shap.md` |

Route elsewhere when the data or field has its own conventions:

- Omics classifiers, biomarker panels, survival ML and atlas mapping: the bio `machine-learning`
  bundle.
- Clinical prediction models, risk scores and EHR cohorts with calibration and safety checks:
  `clinical-ai-modeling`.
- Treatment effects rather than predictions: `causal-heterogeneity-policy-learning`.
- Forecasting future values of a series: `general-time-series-forecasting`.
- Finding a pretrained scientific model or dataset on Hugging Face: `hugging-science-resource-discovery`.
- GPU speed-ups (cuML, multi-GPU) and getting a GPU node: `gpu-compute-optimization` and `ucsf-hpc`.

## Leakage checklist

Run through it before trusting any number:

1. Every preprocessing step that learns from data (scaling, imputation, feature selection,
   target encoding, PCA, oversampling) sits inside the pipeline and is fit on training folds
   only.
2. Features do not encode the label or the future: no post-outcome measurements, no
   identifiers that correlate with site or batch, no aggregate computed over the whole dataset.
3. Duplicates and near-duplicates (the same sample sequenced twice, augmented copies, related
   individuals) do not straddle the split.
4. Hyperparameters are tuned with nested cross-validation or on a validation set; the test set
   is touched once, at the end.
5. For pretrained models, check whether the evaluation data could be in the pretraining corpus.

## Evaluation that survives review

- Report the metric with an interval across folds or by bootstrap over independent units, not
  a single number.
- Show calibration (reliability curve, Brier score) for any probability someone will act on.
- Report performance per subgroup that matters (site, sex, ancestry, batch) and flag gaps.
- Compare models with the same splits and seeds; a difference smaller than fold-to-fold
  variation is not a difference.
- Save the fitted pipeline, the split indices, the random seeds and the package versions.

## Explanations are about the model

SHAP values describe how this model uses features, not how the biology works. Use them to find
leakage (a sample ID or batch variable near the top is a red flag), to check a model against
domain knowledge, and to explain single predictions. Correlated features share credit in ways
that depend on the explainer and masker; say which you used (`references/shap.md` covers the
choice). Do not present SHAP rankings as causal or as biomarker discovery without independent
validation.

## In Biorouter

- Train and evaluate with the Developer shell in a pinned environment; the guides include
  runnable templates (`references/scikit-learn/scripts/classification_pipeline.py`,
  `references/pytorch-lightning/scripts/template_lightning_module.py`,
  `references/shap/scripts/tabular_report.py`).
- Long or GPU training runs go to Wynton through `ucsf-hpc`.
- Figures of results go through `python-visualization`; check the rendered figure with
  `figure-qa` before it leaves the project.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/scikit-learn.md` | Supervised and unsupervised learning, preprocessing, pipelines, model evaluation, tuning |
| `references/pytorch-lightning.md` | LightningModule, Trainer, data modules, callbacks, logging, distributed training |
| `references/transformers.md` | Pipelines, model loading, tokenizers, generation, Trainer fine-tuning, v5 changes |
| `references/torch-geometric.md` | Data and HeteroData, message passing, node, link and graph tasks, scaling, explainability |
| `references/shap.md` | Explainer and masker choice, Explanation objects, plots, multiclass, troubleshooting |
