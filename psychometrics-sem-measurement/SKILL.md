---
name: psychometrics-sem-measurement
description: Develop, validate and model measurement instruments and latent variables, including item analysis and reliability (alpha, omega), exploratory and confirmatory factor analysis, structural equation models with mediation, measurement invariance across groups and time, item response theory, and scale scoring, with R lavaan, psych, semTools and mirt or Python semopy and factor_analyzer. Use for questionnaires, patient-reported outcomes, cognitive tests, scale development, CFA or SEM, fit indices, or comparing latent means across groups.
user-invocable: true
license: Apache-2.0
metadata:
  version: "1.1.0"
  origin: native
  upstream: "none (native rewrite, no upstream text copied)"
---

# Psychometrics, SEM, and Measurement

A scale score is only as meaningful as the evidence that it measures one thing, the same way for
everyone it is compared across. This skill builds that evidence step by step. It is written for
Biorouter and copies no upstream text.

## Match the question to the model

| Question | Model | R | Python |
| --- | --- | --- | --- |
| Do these items hang together; how reliable is the total | Item analysis, coefficient omega (and alpha for comparison) | `psych::alpha`, `psych::omega`, `semTools::compRelSEM` | `pingouin.cronbach_alpha`, `factor_analyzer` |
| How many dimensions are there | Exploratory factor analysis with parallel analysis | `psych::fa.parallel`, `psych::fa` (oblique rotation) | `factor_analyzer.FactorAnalyzer` |
| Does a hypothesised structure fit | Confirmatory factor analysis | `lavaan::cfa` | `semopy` |
| How do latent constructs relate; mediation | Structural equation model | `lavaan::sem` | `semopy` |
| Is the measure equivalent across groups or time | Multi-group CFA invariance (configural, metric, scalar, strict) | `lavaan` with `group.equal`, `semTools::measEq.syntax` | `semopy` multi-group (limited) |
| Item difficulty and discrimination; adaptive tests; short forms | Item response theory (Rasch, 2PL, graded response) | `mirt`, `ltm` | `girth` |
| Change in a latent construct over time | Latent growth curve model | `lavaan::growth` | `semopy` |

R's ecosystem (lavaan, semTools, mirt) is the most complete; use Python when the project is
Python-only and the model is supported.

## Workflow for a new or adapted scale

1. **Construct definition**: what the scale measures, its intended population and use, and its
   expected dimensions, written before looking at data.
2. **Item screening**: distributions, floor and ceiling effects, missingness, corrected
   item-total correlations, and response categories that nobody uses.
3. **Split the sample** when both exploring and confirming: EFA on one half, CFA on the other.
4. **EFA**: decide the number of factors with parallel analysis and interpretability, not
   eigenvalues above one; use an oblique rotation (oblimin, geomin) because constructs correlate;
   use polychoric correlations for ordinal items.
5. **CFA**: specify the model from theory; for ordinal items (fewer than about five categories)
   use WLSMV (`ordered = TRUE` in lavaan); for continuous items with non-normality use MLR.
6. **Reliability**: report omega for each factor (alpha assumes equal loadings and is a lower
   bound otherwise).
7. **Validity evidence**: convergent and discriminant correlations with other measures, known
   groups, criterion relations, and invariance where groups will be compared.

## Reading fit honestly

Report chi-square with degrees of freedom, CFI, TLI, RMSEA with its 90% interval, and SRMR. Common
benchmarks (CFI and TLI near 0.95, RMSEA below about 0.06, SRMR below about 0.08) are guides
from simulation studies, not pass marks; with ordinal estimators they behave differently.
Modification indices are hypotheses: add a parameter only with a substantive reason, report every
change, and confirm modified models on new data.

## Measurement invariance

Test in order: configural (same structure), metric (equal loadings), scalar (equal intercepts or
thresholds), and strict (equal residuals) if needed. Compare nested models with the change in CFI
(a drop greater than about 0.01 suggests non-invariance) and scaled chi-square difference tests.
Latent means can be compared only under at least partial scalar invariance; identify which items
are non-invariant and say so. Comparing observed sum scores across groups assumes invariance
that has not been shown.

## SEM and mediation

Draw the model first (a path diagram makes assumptions explicit). Indirect effects need
bootstrapped confidence intervals (`se = "bootstrap"` in lavaan or a Monte Carlo interval), and
mediation is a causal claim: with cross-sectional data, say so and run
`causal-identification-gates`. Check identification (at least three indicators per factor, or
constraints), Heywood cases (negative variances) and convergence warnings before reading results.

## Missing data and samples

Use full-information maximum likelihood (`missing = "fiml"` in lavaan) or multiple imputation
rather than listwise deletion. Survey data with weights and clusters need `sampling.weights` and
`cluster` in lavaan (see `survey-weights-complex-samples`). Rules of thumb for sample size are
weak; simulate power for the planned model when it matters (`simsem`, or `statistical-modeling-bayes`).

## Reporting

Report the model specification (or syntax as a supplement), estimator, handling of missing data,
fit indices with intervals, standardised loadings with standard errors, factor correlations,
reliability per factor, invariance steps and decisions, and software versions. Instruments under
copyright (many clinical and cognitive scales) need the owner's licence to reproduce items.

## Related skills

- `survey-weights-complex-samples` for estimates from weighted survey samples.
- `statistical-modeling-bayes` for Bayesian SEM (`blavaan`) and models of observed variables.
- `qualitative-thematic-analysis` for cognitive interviews during item development.
- When gptr Agent is installed, fit lavaan and mirt models in the person's live R session; R style
  follows `r-scripting`.
