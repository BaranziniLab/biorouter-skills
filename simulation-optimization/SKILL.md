---
name: simulation-optimization
description: Build discrete-event simulations of queues, resources and processes with SimPy, and solve single-, multi- and many-objective optimisation problems with pymoo (NSGA-II, NSGA-III, MOEA/D, constraints, Pareto fronts). Use for clinic, lab or pipeline throughput and waiting-time models, capacity planning, warm-up and replication analysis, design trade-offs between competing objectives, or choosing a solution from a Pareto front.
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/simpy, skills/pymoo)"
---

# Simulation and Optimization

Two related jobs live here: **simulating** a system that is too complex for a formula (patients
moving through a clinic, samples through a sequencing core, jobs through a cluster), and
**optimising** a design whose objectives conflict (cost against accuracy, throughput against
waiting time). The guides under `references/` are adapted from K-Dense Scientific Agent Skills
(see `LICENSE-UPSTREAM`).

## Choose the path

| Question | Use | Guide |
| --- | --- | --- |
| How long will people or samples wait, how busy are resources, what happens if we add a machine or change a schedule | Discrete-event simulation with SimPy | `references/simpy.md` |
| What design minimises one objective under constraints | pymoo single-objective algorithms (GA, DE, CMA-ES via wrappers) or a classical solver if the problem is smooth | `references/pymoo.md` |
| What are the best trade-offs between two or three objectives | NSGA-II or MOEA/D in pymoo, then a decision-making step | `references/pymoo.md` |
| Four or more objectives | NSGA-III or MOEA/D with reference directions | `references/pymoo/references/algorithms.md` |
| Which inputs of a simulation matter, or the best settings of a simulated system | Simulation inside the optimisation loop, with replications per evaluation | both guides |

Prefer a closed-form answer when one exists: an M/M/c queue with stable arrivals has formulas,
and a linear program has exact solvers (SciPy `linprog`, OR-Tools). Simulation and evolutionary
search are for problems that formulas and convex solvers cannot handle.

Route elsewhere for:

- Branch-and-prune improvement of a research artefact, prompt or analysis plan:
  `arbor-optimization`.
- Fluid and other continuum physics: `computational-fluid-dynamics`.
- Forecasting arrivals or demand to feed a simulation: `general-time-series-forecasting`.

## Building a simulation that can be trusted

1. **Write the conceptual model first**: entities, resources, the sequence of activities, the
   decision rules (priority, routing), and what is measured. Get the person to confirm it
   before coding.
2. **Fit inputs to data.** Arrival and service-time distributions come from observed data
   (check fit, do not default to exponential); document the source and period.
3. **Verify, then validate.** Verification: the code does what the conceptual model says
   (trace a few entities with `references/simpy/scripts/event_trace_summary.py`). Validation:
   simulated outputs match a real period the inputs were not fitted on.
4. **Warm-up and run length.** Discard a warm-up period for steady-state questions, chosen
   from a plot of the output over time, and run long enough that the interval width is
   acceptable.
5. **Independent replications.** Run many replications with different seeds and report means
   with confidence intervals across replications
   (`references/simpy/scripts/replication_runner.py`). One run is an anecdote.
6. **Compare scenarios with common random numbers** so differences reflect the change, not the
   noise.

## Optimising without fooling yourself

- **State objectives, variables and constraints** explicitly, with units and bounds. Encode
  constraints as constraints (pymoo's `G` and `H`), not as arbitrary penalties.
- **Normalise objectives** before comparing or weighting them; a cost in dollars and an error
  rate in percent are not on one scale.
- **Run several seeds** and report the spread of the final front or best value; evolutionary
  algorithms are stochastic.
- **Check convergence** with a running metric (hypervolume or IGD against a reference) rather
  than a fixed number of generations.
- **Benchmark the setup** on a known problem (ZDT, DTLZ) when building something new.
- **Decision-making is a separate step.** A Pareto front is not an answer; choose with the
  person, using stated preferences, a knee point or compromise programming
  (`references/pymoo/scripts/decision_making_example.py`).

## In Biorouter

Run models with the Developer shell; both guides ship runnable examples and validators
(`references/simpy/scripts/validate_simulation_config.py`,
`references/pymoo/scripts/multi_objective_example.py`). Many replications or expensive
evaluations parallelise well on Wynton through `ucsf-hpc`. Results and fronts go through
`python-visualization`.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/simpy.md` | Environment and events, processes, interrupts, shared resources, monitoring, real-time runs, replications, testing |
| `references/pymoo.md` | Problem definitions, algorithm selection, constraints, operators, benchmarks, parallelisation, visualisation, decision making |
