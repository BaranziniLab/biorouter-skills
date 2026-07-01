---
name: computational-fluid-dynamics
description: Plan and review computational fluid dynamics workflows with meshes, boundary conditions, turbulence models, OpenFOAM/FluidSim-style solvers, validation cases, convergence checks, and reproducible simulation artifacts. Use when users mention CFD, fluid dynamics, Navier-Stokes, meshing, turbulence, OpenFOAM, or flow simulation.
user-invocable: true
license: Apache-2.0
---

# Computational Fluid Dynamics

Source adaptation: BioRouter-original synthesis inspired by Scientific Agent Skills computational-fluid-dynamics patterns, rewritten under Apache-2.0.

## When to Use

Use this skill when the user asks for CFD, fluid simulation, turbulence, meshing, boundary-condition design, solver setup, or validation of flow results. Use `simulation-optimization` for broad simulation/optimization tasks; use this skill when the physics is fluid dynamics.

## Intake

Collect:

- Flow regime, geometry, dimensionality, and governing equations.
- Fluid properties, compressibility, multiphase/reactive status, and thermal coupling.
- Boundary and initial conditions.
- Solver/tool target: OpenFOAM, FluidSim, SU2, FiPy, FEniCS, custom Python, or commercial export.
- Mesh type, refinement strategy, and expected near-wall treatment.
- Validation target: analytic solution, benchmark case, experiment, or prior simulation.
- Compute budget and required deliverable.

## Setup Checklist

1. State governing equations and assumptions.
2. Define domain, coordinate system, units, and nondimensional numbers.
3. Specify inlet/outlet/wall/symmetry/periodic conditions.
4. Choose laminar, RANS, LES, DNS, or reduced-order modeling deliberately.
5. Plan mesh generation, quality checks, and grid-independence tests.
6. Define time step, Courant number, residual criteria, and write intervals.
7. Preserve solver version, dictionaries/config files, mesh files, and run logs.

## Validation and Convergence

Do not trust a CFD result until these are addressed:

- Mesh quality and grid convergence.
- Residual convergence and mass/energy balance.
- Sensitivity to time step, boundary conditions, and turbulence model.
- Comparison to an analytic, experimental, or accepted benchmark case.
- Clear distinction between qualitative visualization and quantitative prediction.

## BioRouter Routes

- Use `physical-science-computing` for unit systems, coordinates, and physical constants.
- Use `simulation-optimization` when optimizing design parameters or running sweeps.
- Use `gpu-compute-optimization` for large GPU-bound solvers.
- Use `replication-package-audit` before publishing a CFD workflow or figure.
- Use `scientific-visual-communication` for flow-field figures and annotated schematics.

## Output Shape

Return: physics framing, solver route, mesh/boundary plan, validation checklist, convergence criteria, expected artifacts, and risks that would invalidate the result.
