---
name: chemoinformatics-deepchem-drug-discovery
description: Build DeepChem-style molecular machine-learning workflows for QSAR, ADMET, virtual screening, featurization, dataset splitting, model evaluation, and uncertainty-aware hit ranking. Use when a drug-discovery task needs molecule ML beyond simple RDKit descriptors.
tool_type: python
primary_tool: deepchem
user-invocable: false
license: Apache-2.0
---

# DeepChem Drug Discovery

Use DeepChem for molecular ML only after compound hygiene has passed through `chemoinformatics/datamol-medchem`.

## Gate Checks

- Split strategy matches the scientific question: scaffold split for prospective generalization, random split only for narrow interpolation.
- Labels, units, censoring, and assay direction are documented.
- Duplicates and near-duplicates do not leak across splits.
- Baseline models are included before deep models.
- Evaluation metrics match task type and class imbalance.

## Workflow

1. Load curated molecules and assay labels.
2. Choose featurizer: circular fingerprints, graph convolution, transformer embeddings, or descriptors.
3. Split by scaffold or time when possible.
4. Train baseline and candidate models.
5. Evaluate with confidence intervals or repeated splits.
6. Explain hit ranking with applicability-domain warnings.

## Reporting Rules

- Do not call a model "validated" from a random split alone.
- Report external validation separately from cross-validation.
- Include failed featurization counts.
- Rank compounds with uncertainty or applicability-domain flags when possible.

## Related Skills

- `chemoinformatics/datamol-medchem`
- `chemoinformatics/molecular-descriptors`
- `machine-learning/model-explainability-shap`
