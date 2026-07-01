---
name: molecular-dynamics
description: Plan and review molecular dynamics simulations and trajectory analysis with OpenMM, GROMACS, AmberTools, MDAnalysis, MDTraj, and reproducibility checks. Use when users ask about MD setup, force fields, equilibration, production runs, trajectories, RMSD/RMSF, or binding/stability dynamics.
user-invocable: true
license: Apache-2.0
---

# Molecular Dynamics

Source adaptation: BioRouter-original synthesis inspired by Scientific Agent Skills molecular-dynamics patterns, rewritten under Apache-2.0.

## When to Use

Use this skill for molecular dynamics setup, execution planning, or trajectory analysis. Prefer `ProteinStructureAgent`, `ChemoinformaticsAgent`, `RowanMolecularModelingAgent`, or `TamarindBioAgent` when live structure/platform data or cloud jobs are needed.

## Intake

Collect:

- Molecular system: protein, ligand, membrane, nucleic acid, solvent, ions, mutations.
- Starting structure and provenance: PDB, AlphaFold, docking pose, modeled complex.
- Intended question: stability, conformational change, binding, mutation effect, ensemble, or method validation.
- Force field, water model, protonation state, and ligand parameters.
- Compute environment and runtime budget.
- Required outputs: protocol, command plan, analysis code, report, or review.

## Setup Checklist

1. Validate structure completeness, chain IDs, missing residues, alternate locations, ligands, cofactors, and crystal artifacts.
2. Decide protonation/tautomer states and document pH assumptions.
3. Select force field and parameterization path appropriate to the system.
4. Define box, solvent, ion concentration, constraints, timestep, temperature, and pressure coupling.
5. Plan minimization, heating, equilibration, and production stages.
6. Preserve random seeds, package versions, inputs, and run metadata.

## Analysis Checklist

- RMSD/RMSF and alignment choices.
- Radius of gyration, contacts, hydrogen bonds, distances, angles, or dihedrals.
- Ligand stability, binding-site contacts, and water/ion interactions.
- Clustering, PCA/tICA, free-energy summaries, or Markov-state models only when sampling supports them.
- Replicate agreement and convergence diagnostics.

## Quality Gates

Do not overclaim from MD:

1. State simulation length, replicates, force field, and system preparation.
2. Distinguish exploratory dynamics from thermodynamic conclusions.
3. Report uncertainty or replicate variability.
4. Flag insufficient sampling, bad starting structures, or unvalidated ligand parameters.
5. Include rerunnable commands or notebooks when execution is requested.

## Output Shape

Return: system summary, setup plan, execution commands or pseudocode, analysis plan, expected artifacts, and validation risks.
