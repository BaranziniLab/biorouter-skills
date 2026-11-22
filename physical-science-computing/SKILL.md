---
name: physical-science-computing
description: Get physical calculations right with tracked units and propagated measurement uncertainty (pint, uncertainties, GUM budgets, Monte Carlo), exact symbolic maths with SymPy (algebra, calculus, solving, linear algebra, code generation), and astronomy data with Astropy (units, coordinates, FITS, tables, time scales, WCS, cosmology). Use for unit conversion and dimensional checks, error propagation, significant figures, deriving or simplifying equations, or astronomical data analysis.
user-invocable: true
license: Apache-2.0 AND MIT AND BSD-3-Clause
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/uncertainty-and-units, skills/sympy, skills/astropy)"
---

# Physical Science Computing

Three habits separate a physical result from a number: it carries **units**, it carries an
**uncertainty**, and the algebra behind it can be **checked**. This skill covers all three, plus
astronomy data, where those habits are built into Astropy. The guides under `references/` are
adapted from K-Dense Scientific Agent Skills (see `LICENSE-UPSTREAM`).

## Choose the path

| Task | Use | Guide |
| --- | --- | --- |
| Convert units, check dimensions, catch unit errors in code or a paper, handle offset temperatures and logarithmic units | pint | `references/uncertainty-and-units.md` |
| Propagate measurement uncertainty, build a GUM uncertainty budget, Type A and Type B evaluation, coverage factors, Monte Carlo propagation, report value plus or minus uncertainty | uncertainties, NumPy and SciPy, following the GUM | `references/uncertainty-and-units.md` |
| Derive, simplify, differentiate, integrate or solve equations exactly; symbolic matrices; series; generate NumPy or C code from an expression | SymPy | `references/sympy.md` |
| Astronomical units and constants, sky coordinates and frames, FITS images and tables, time scales (UTC, TAI, TDB), WCS, cosmological distances | Astropy | `references/astropy.md` |

Route elsewhere for:

- Quantum circuits and quantum-system dynamics: `quantum-scientific-computing`.
- Flow simulation: `computational-fluid-dynamics`; molecular simulation: `molecular-dynamics`.
- Statistical models of measured data (regression, hierarchical models): `statistical-modeling-bayes`.

## Units: rules that prevent silent errors

1. **Attach units at input and strip them only at output**, with the unit named in the column
   header or label. A bare float in the middle of a calculation is where scale errors hide.
2. **Temperatures with offsets** (Celsius, Fahrenheit) cannot be multiplied or added like
   kelvin; pint makes this explicit with delta units.
3. **Logarithmic units** (dB, pH, magnitudes) add by multiplying the underlying quantity;
   convert before summing.
4. **Check plausibility.** A computed body mass of 7,000 kg or a reaction time of 3 ns is a
   unit error until shown otherwise (`references/uncertainty-and-units/scripts/check_plausibility.py`).
5. **Audit existing code** for unit handling before trusting it
   (`references/uncertainty-and-units/scripts/audit_units.py`).

## Uncertainty: the GUM in practice

- List every input with its standard uncertainty, its type (A: from repeated measurements; B:
  from certificates, specifications, resolution) and its distribution.
- Propagate with first-order (linear) propagation when the model is close to linear over the
  uncertainty range; otherwise, or when in doubt, use Monte Carlo propagation and compare.
- Keep correlations. The `uncertainties` package tracks them through arithmetic, but a round
  trip through floats or a CSV destroys them; the guide shows how to keep covariance matrices.
- Report a combined standard uncertainty, or an expanded uncertainty with its coverage factor
  (k = 2 for about 95% under normality), with the value rounded to match: two significant
  figures of uncertainty at most (`references/uncertainty-and-units/scripts/format_result.py`).
- An uncertainty budget table (input, value, standard uncertainty, sensitivity coefficient,
  contribution) shows where to improve the measurement
  (`references/uncertainty-and-units/scripts/uncertainty_budget.py`).

## Symbolic maths: keep it exact until the end

- Declare symbols with assumptions (`positive=True`, `real=True`); many simplifications only
  apply under them.
- Use `Rational` or integers rather than floats in symbolic work; a float early on spoils exact
  results.
- Verify every solution by substituting it back, and check limiting cases and dimensions of
  the result.
- Convert to numerical code with `lambdify` once the expression is final; do not evaluate
  symbolic expressions in a loop.
- Do not call `sympify` or the parsers on untrusted strings; they can evaluate code. The guide
  explains safer parsing.

## Astronomy notes

Use `Quantity` everywhere, `SkyCoord` with an explicit frame and epoch, `Time` with an explicit
scale, and read WCS from the FITS header rather than assuming pixel scales. Remote lookups
(name resolution, IERS tables) need network access; record when they were fetched.

## In Biorouter

Run calculations with the Developer shell; the units and uncertainty guide ships local CLIs that
need no network (`references/uncertainty-and-units/scripts/propagate_uncertainty.py`,
`references/uncertainty-and-units/scripts/convert_units.py`). Equations for a manuscript can be
exported from SymPy as LaTeX.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/uncertainty-and-units.md` | pint and uncertainties recipes, GUM method, budgets, Monte Carlo, reporting rules, plausibility scales, domain conversions |
| `references/sympy.md` | Symbols and assumptions, simplification, calculus, solving, matrices, physics modules, printing and code generation |
| `references/astropy.md` | Units and quantities, coordinates, cosmology, FITS, tables, time, WCS and other modules |
