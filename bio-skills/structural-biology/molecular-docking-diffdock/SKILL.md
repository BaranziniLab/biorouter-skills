---
name: structural-biology-molecular-docking-diffdock
description: Run or plan DiffDock-style learned molecular docking workflows, including ligand/protein preparation, binding-site assumptions, pose confidence interpretation, and comparison to classical docking. Use when a docking task needs learned pose prediction rather than AutoDock Vina alone.
tool_type: mixed
primary_tool: diffdock
user-invocable: false
license: Apache-2.0
---

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
- `chemoinformatics/datamol-medchem`
- `structural-biology/protein-structure-prediction`
