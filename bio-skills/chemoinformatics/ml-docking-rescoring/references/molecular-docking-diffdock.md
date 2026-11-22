# DiffDock-style pose prediction

> Merged from the former `molecular-docking-diffdock` component (Biorouter original, bundle version 1.0.0) into `ml-docking-rescoring` at 1.1.0. Nothing was dropped; the text below is the former component as written.

# DiffDock-Style Molecular Docking

Use this skill when the user asks for learned molecular docking or pose prediction. For classical docking, use `chemoinformatics/virtual-screening`.

## Gate Checks

- Protein structure source, chain, protonation, cofactors, and missing residues are documented.
- Ligands have passed compound hygiene and 3D/protonation preparation.
- Binding site is known, inferred, or blind-docking assumptions are explicit.
- Pose confidence is not treated as binding affinity.
- Results are compared to controls or classical docking when possible.

## Workflow

1. Prepare protein and ligand files.
2. Define docking mode and binding-site assumptions.
3. Run DiffDock or compatible learned docking model.
4. Inspect top poses, steric clashes, and interaction plausibility.
5. Compare against known ligand, docking baseline, or structural biology evidence.
6. Export pose files and a ranked summary.

## Reporting Rules

- Report pose confidence separately from affinity or activity.
- State all structure-preparation assumptions.
- Do not claim a hit without orthogonal evidence or validation.

## Related Skills

- `chemoinformatics/virtual-screening`
- `chemoinformatics/molecular-standardization`
- `structural-biology/protein-structure-prediction`


## Usage guide (former `usage-guide.md`)

# DiffDock-Style Docking Usage Guide

Example prompts:

- "Dock this ligand set with DiffDock and compare poses to Vina."
- "Prepare a protein-ligand docking workflow and document assumptions."
- "Rank poses by confidence but do not interpret confidence as affinity."

The agent will keep pose prediction, affinity, and biological validation separate.
