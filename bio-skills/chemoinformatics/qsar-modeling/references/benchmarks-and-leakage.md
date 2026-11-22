# Benchmarks, splits and leakage for compound models

> Absorbed from the former core skill `drug-discovery-benchmarks` (now a redirect to the chemoinformatics bundle). Biorouter original, Apache-2.0.

Use this when the question is whether a compound model, ADMET predictor or virtual-screening result can be trusted, not how to build it.

## What to pin before reporting a number

- **Dataset and version.** Name the benchmark (for example a TDC ADMET group task, MoleculeNet set, or an in-house assay table), its release, and the exact split file or seed. A score without the split is not comparable.
- **Assay provenance.** Record the assay type, units, species or cell line, and the source database or paper for each label. Merge measurements only when the assay definitions match; log-transform units (pIC50, logS) before pooling.
- **Split type.** Report random, scaffold (Bemis-Murcko) and, where the claim is about new chemistry, cluster or temporal splits. A random split alone overstates performance for compounds from new series.
- **Leakage checks.** Standardise structures first (see `molecular-standardization`), then check that no canonical SMILES, InChIKey or near-duplicate (Tanimoto of 0.9 or more on Morgan fingerprints) appears on both sides of a split. Check that activity cliffs, salts and stereoisomers did not slip across.
- **Baselines.** Include a trivial baseline (mean or majority class), a fingerprint random forest, and a published reference on the same split before claiming a gain.
- **Uncertainty and applicability.** Give a confidence interval from repeated splits or bootstrapping, and say how far test compounds sit from the training set.
- **Virtual screening.** Report enrichment factor at 1% and 5% and the number of actives and decoys; state how decoys were made and whether they were property-matched.

## Verification checklist

1. Every compound on both sides of each split passed the same standardisation.
2. No identifier overlap between train, validation and test.
3. The metric matches the decision (AUROC and AUPRC for classification, RMSE and Spearman for regression, EF for screening).
4. The result is rerun from a recorded seed and split file.
5. Anything that needs proprietary data, a live service or wet-lab confirmation is marked unverified.
