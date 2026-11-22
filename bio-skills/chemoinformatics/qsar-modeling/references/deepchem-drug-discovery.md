# DeepChem-style workflows

> Merged from the former `deepchem-drug-discovery` component (Biorouter original, bundle version 1.0.0) into `qsar-modeling` at 1.1.0. Nothing was dropped; the text below is the former component as written.

# DeepChem Drug Discovery

Use DeepChem for molecular ML only after compound hygiene has passed through `chemoinformatics/molecular-standardization`.

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

- `chemoinformatics/molecular-standardization`
- `chemoinformatics/molecular-descriptors`
- `machine-learning/prediction-explanation`


## Usage guide (former `usage-guide.md`)

# DeepChem Drug Discovery Usage Guide

Example prompts:

- "Train a QSAR model with a scaffold split and compare it to a random forest baseline."
- "Predict ADMET endpoints and flag compounds outside the applicability domain."
- "Set up a DeepChem graph model for this curated molecule table."

The agent will choose splits carefully and avoid overstating random-split results.
