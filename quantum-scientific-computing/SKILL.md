---
name: quantum-scientific-computing
description: Build, simulate and run quantum circuits and quantum-system models with Qiskit, Cirq, PennyLane and QuTiP, from local statevector and noisy simulation to IBM or Google hardware, variational algorithms, quantum chemistry, and open-system dynamics with master equations. Use when someone asks about qubits, circuits, transpilation, Sampler or Estimator primitives, VQE, QAOA, quantum machine learning, noise models, Lindblad or Monte Carlo trajectory solvers, or steady states and spectra.
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/qiskit, skills/cirq, skills/pennylane, skills/qutip)"
---

# Quantum Scientific Computing

Quantum results are easy to overstate: a noiseless simulation of six qubits says little about
hardware, and an optimiser that converged on a simulator may not on a device. This skill picks
the framework that fits the question and keeps simulation, noise and hardware claims separate.
The four guides under `references/` are adapted from K-Dense Scientific Agent Skills (see
`LICENSE-UPSTREAM`).

## Pick the framework by the question

| Question | Use | Guide |
| --- | --- | --- |
| Gate-model circuits for IBM hardware; Sampler and Estimator primitives; target-aware transpilation; local or noisy simulation with Aer; Runtime sessions and error mitigation | Qiskit 2.x | `references/qiskit.md` |
| Circuits for Google Quantum AI hardware, moment-level control, custom noise models, characterisation experiments | Cirq | `references/cirq.md` |
| Differentiable circuits, variational algorithms (VQE, QAOA), quantum machine learning with PyTorch or JAX, molecular Hamiltonians | PennyLane | `references/pennylane.md` |
| Physics of a quantum system itself: Hamiltonians, open-system dynamics (Lindblad master equation, Monte Carlo trajectories), steady states, spectra, Wigner functions | QuTiP 5 | `references/qutip.md` |

The guides cross-reference each other: Cirq and PennyLane send hardware-specific compilation to
Qiskit or Cirq, and open-system physics to QuTiP. Follow those pointers inside this skill.

## Work in three tiers, and label each result

1. **Ideal simulation** (statevector or exact solver): checks that the circuit or model is what
   you meant. Verify against an analytic case first (a Bell state, a two-level Rabi
   oscillation, a known ground-state energy).
2. **Noisy simulation**: a noise model from device calibration data or a stated
   depolarising and readout model. This is the honest estimate of what hardware might give.
3. **Hardware**: only after tiers 1 and 2 agree with expectations. Record the backend name,
   calibration date, transpiled depth and two-qubit gate count, shots, and any error
   mitigation.

Never report a tier-1 or tier-2 number as if it came from hardware.

## Checks that catch the usual mistakes

- **Qubit ordering.** Qiskit is little-endian (qubit 0 is the rightmost bit in a bitstring);
  Cirq and PennyLane order wires as declared. Check a single-qubit X on qubit 0 before trusting
  any histogram.
- **Transpiled cost, not drawn cost.** Report depth and two-qubit gate count after
  transpilation for the target; a circuit that is shallow on paper can triple on real
  connectivity.
- **Shots and uncertainty.** Expectation values from sampling carry shot noise; report the
  standard error or a bootstrap interval and the number of shots.
- **Optimiser convergence.** For VQE and QAOA, run several initialisations, plot the cost
  history, and compare with the exact answer for a small instance. Barren plateaus show up as
  vanishing gradients; note when they do.
- **Dimensions and truncation in QuTiP.** Check `dims` of every operator and state, and show
  that results do not change when a truncated Hilbert space (photon number, levels) is enlarged
  (`references/qutip/scripts/convergence_sweep.py`).
- **Solver choice follows physics.** Closed system: `sesolve`. Markovian open system with few
  levels: `mesolve`. Large open system or individual trajectories: `mcsolve`. Say why the
  Markovian assumption holds.

## Credentials and cost

IBM Quantum, Google and cloud providers need accounts and API tokens; keep them in the
provider's own configuration or environment variables, never in code or notebooks. Hardware
time can be billed: state the expected shots and jobs before submitting, and get the person's
agreement for anything beyond a small test.

## In Biorouter

- Run simulations with the Developer shell in an environment pinned to the versions each guide
  names (Qiskit, Cirq, PennyLane and QuTiP pin different NumPy and Python ranges; separate
  environments avoid conflicts).
- Large classical simulations can run on Wynton through `ucsf-hpc`. Qiskit Aer has a GPU build;
  the general method for moving and benchmarking work on a GPU is in `gpu-compute-optimization`.
- Units, constants and symbolic derivations around a model go through `physical-science-computing`.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/qiskit.md` | Qiskit 2.x circuits, primitives, transpilation, Aer, IBM Runtime, migration notes, testing |
| `references/cirq.md` | Circuit building, simulation, transformation, Google hardware, noise, experiments |
| `references/pennylane.md` | QNodes, devices, optimisation, quantum chemistry, quantum ML, provider plugins |
| `references/qutip.md` | Qobj and dimensions, solvers, time dependence, trajectories, steady states, spectra, visualisation |
