---
name: materials-informatics
description: Analyse, convert and query crystalline and inorganic materials with pymatgen and compute CALPHAD phase equilibria with pycalphad, including CIF and POSCAR structures, symmetry, phase diagrams and energy above hull, band structures and DOS from VASP or Q-Chem, Materials Project queries, and alloy phase fractions from TDB databases. Use for crystal structures, materials screening, phase stability, or computed materials data.
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/pymatgen, skills/pycalphad)"
---

# Materials Informatics

Materials results depend on settings that are easy to lose: the symmetry tolerance used to
assign a space group, the functional and corrections behind a computed energy, the database a
phase diagram was built from. This skill keeps those settings attached to every number. The two
guides under `references/` are adapted from K-Dense Scientific Agent Skills (MIT; see
`LICENSE-UPSTREAM`).

## Choose the path

| Task | Use | Guide |
| --- | --- | --- |
| Read, validate and convert structures (CIF, POSCAR, XYZ), build supercells, substitute sites, compare structures | pymatgen `Structure`, `Molecule`, transformations, `StructureMatcher` | `references/pymatgen.md` |
| Space groups and symmetry; sensitivity of the assignment to tolerance | pymatgen `SpacegroupAnalyzer` (spglib) | `references/pymatgen.md`, `references/pymatgen/scripts/symmetry_sensitivity_report.py` |
| Phase stability from computed energies: convex hull, energy above hull, decomposition products | pymatgen `PhaseDiagram` with compatible entries | `references/pymatgen.md`, `references/pymatgen/scripts/phase_diagram_generator.py` |
| Band structures, density of states and other outputs from VASP, Q-Chem and similar codes | pymatgen I/O and electronic-structure modules | `references/pymatgen/references/io_formats.md`, `references/pymatgen/references/analysis_modules.md` |
| Query the Materials Project | `mp-api` with a key, planned and bounded before any call | `references/pymatgen/references/materials_project_api.md` |
| Finite-temperature alloy equilibria, phase fractions and compositions, temperature sweeps from a TDB database | pycalphad | `references/pycalphad.md` |

Route elsewhere for:

- Molecular dynamics of materials or biomolecules: `molecular-dynamics`.
- Small molecules, drug-like chemistry and cheminformatics descriptors: the `chemoinformatics`
  bundle.
- Quantum-mechanical model Hamiltonians and open-system dynamics: `quantum-scientific-computing`.
- Units and uncertainty in derived quantities: `physical-science-computing`.

## Rules for structures

1. **Validate on intake.** Check composition, charge balance where expected, site occupancies,
   minimum interatomic distances and lattice parameters against the source before analysis
   (`references/pymatgen/scripts/composition_structure_validator.py`). CIFs from the literature
   often carry partial occupancies or disorder that pymatgen will read but a calculation cannot
   use directly.
2. **Report the symmetry tolerance.** A space group assigned at `symprec=0.1` can differ from
   one at `0.01`. Run the sensitivity report and state the tolerance with the result.
3. **Keep provenance in the object.** Record the source (database id, DOI, file) and every
   transformation applied, in order, alongside the output structure
   (`references/pymatgen/scripts/artifact_manifest.py`).

## Rules for energies and phase diagrams

- **Compatible entries only.** Energies from different functionals (PBE, PBE+U, r2SCAN) or
  different correction schemes cannot sit on one hull. Use the Materials Project compatibility
  scheme consistently, or compute everything at one level of theory, and say which.
- **Energy above hull is model-dependent.** Report it with the functional and correction set,
  and treat small positive values (tens of meV per atom) as possibly synthesisable rather than
  unstable; metastable phases are common.
- **Plan network queries.** Materials Project queries need an API key from the environment and
  should request only the fields and chemical systems needed; the guide shows the bounded
  pattern. Cite the database version used.

## Rules for CALPHAD

- Conditions must be complete: components, phases considered, temperature, pressure and
  enough mole-fraction conditions to fix the system (the pycalphad guide lists them).
- Results are only as good as the thermodynamic database. The bundled
  `references/pycalphad/assets/ideal-cu-ni.tdb` is a teaching database; real alloy predictions
  need an assessed, appropriately licensed TDB, and its source must be cited.
- Check lever-rule consistency of phase fractions and compare with at least one experimental
  point from the literature before trusting a new prediction.

## In Biorouter

Run calculations with the Developer shell in an environment pinned to the guide's versions
(pymatgen releases often change APIs). Heavy DFT post-processing or large screening runs go to
Wynton through `ucsf-hpc`. Phase-diagram and band-structure figures go through
`python-visualization` and `figure-qa`.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/pymatgen.md` | Core classes, safe structure intake, symmetry, conversion and I/O, transformations, phase diagrams, electronic structure, Materials Project |
| `references/pycalphad.md` | TDB databases, equilibrium calculations, phase fractions, temperature sweeps, acceptance checks |
