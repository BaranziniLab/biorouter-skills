---
name: statistical-modeling-bayes
description: Choose, fit, check and report statistical models, from t-tests and ANOVA through GLMs, mixed models and time series to Bayesian models in PyMC or brms, with power and sample-size planning. Use when someone wants to compare groups, test a hypothesis, pick a model or test, check assumptions, compute effect sizes, plan how many samples they need, fit a hierarchical or Bayesian model, run MCMC diagnostics, or write up results, even if they never name the method.
user-invocable: true
license: Apache-2.0 AND MIT AND BSD-3-Clause
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/statistical-analysis, skills/statistical-power, skills/statsmodels, skills/pymc); ab604/claude-code-r-skills@529de4fcfe68fcc7c30cc56388bb625e8ddf37f0 (.claude/skills/r-bayes)"
---

# Statistical Modeling and Bayes

This skill turns a research question into the right statistical model, fits it, checks it and
reports it honestly. It holds the decisions; the five guides under `references/` hold the code.
They are adapted from K-Dense Scientific Agent Skills and ab604/claude-code-r-skills, with
licences in `LICENSE-UPSTREAM`.

## Before any model

Write these down with the person, in their words, before touching data:

- **The question as a contrast.** "Is the mean of X different between A and B", "how much does
  Y change per unit of Z", "what is the probability that the effect exceeds a clinically useful
  size". The contrast decides the estimand, and the estimand decides the model.
- **The unit of analysis and the independent unit.** Repeated measures on one animal, cells
  within a donor, students within schools, or time points within a patient are not independent.
  Name the level at which replication happened; it sets the sample size and the random effects.
- **Outcome type.** Continuous, binary, count, proportion, ordinal, time to event, or
  compositional. Each has a family; a log transform is not a substitute for a count model.
- **Design.** Experiment or observational; randomised or not; paired, blocked, crossed or
  nested. If someone asks whether X causes Y in observational data, run `causal-identification-gates`
  first.
- **Planned versus exploratory.** Which comparisons were planned before seeing the data. Only
  those get confirmatory language; everything else is labelled exploratory.

## Choose the route

| Situation | Route | Guide |
| --- | --- | --- |
| Compare two or more groups, test association, pick a test, check assumptions, report in APA style | Classical tests with effect sizes and confidence intervals | `references/statistical-analysis.md` |
| How many samples, replicates or participants; minimum detectable effect; power curve; justify a sample size for a grant or IRB | Closed-form power, or simulation when the design is complex | `references/statistical-power.md` |
| Regression with coefficients and inference in Python: OLS, GLM, logistic, Poisson and negative binomial, mixed models, ARIMA | statsmodels | `references/statsmodels.md` |
| Hierarchical models, small samples with informative priors, measurement-error models, full posterior uncertainty in Python | PyMC with ArviZ | `references/pymc.md` |
| The same in R, with multilevel formulas, DAG-based adjustment sets and marginal effects | brms with dagitty, tidybayes and marginaleffects | `references/r-bayes-brms.md` |

Hand off rather than stretch:

- Clinical trials, survival endpoints, randomisation and interim analyses: the
  `clinical-biostatistics` bundle.
- Panel data, event studies, difference in differences and clustered standard errors for
  policy questions: `econometrics-toolkit`.
- Survey weights, strata and clusters: `survey-weights-complex-samples`.
- Latent variables, factor analysis and SEM: `psychometrics-sem-measurement`.
- Differential expression and other omics count models: the matching bio bundle
  (`differential-expression`, `single-cell`), whose tools model dispersion properly.

## Frequentist or Bayesian

Either is defensible; the choice should follow the question, not habit.

- Use **frequentist** models when the field expects p-values and intervals, the model is
  standard, the sample is reasonable, and priors would be hard to justify to reviewers.
- Use **Bayesian** models when the question is a probability statement about the effect, the
  structure is hierarchical with few units per group (partial pooling helps), the likelihood
  is custom, or prior information is real and documented.
- In a Bayesian model, priors are part of the model: run prior predictive checks, report the
  priors, and show a sensitivity analysis with a weaker prior when the result depends on it.

## Checks that make the result trustworthy

1. **Assumptions against the data, not by ritual.** Look at residuals against fitted values,
   residual distributions and leverage for linear models; dispersion for counts; separation for
   logistic models. Prefer robust standard errors or a better family over a test of normality.
2. **Convergence and fit.** For mixed models, check for singular fits and warnings. For MCMC,
   R-hat at or below 1.01, adequate effective sample size for every reported quantity, no
   divergences, and posterior predictive checks that resemble the data.
3. **Effect sizes with intervals.** Report the estimate and its 95% interval (confidence or
   credible) in the outcome's units, then the standardised size if the field uses one. A
   p-value alone is never the result.
4. **Multiplicity.** Count the tests. Adjust within families of related comparisons (Holm,
   Benjamini-Hochberg) or pre-specify one primary comparison.
5. **Sensitivity.** Show the result under the most plausible alternative choice: outlier
   handling, covariate set, family, or prior.
6. **Power is for planning.** Never compute "observed power" after the fact; report the
   interval and, if useful, the smallest effect the study could have detected.

## Reporting

State, in order: the model and its family, the outcome and predictors, how the independent
unit was handled, the software and version, the estimate with its interval, and any deviation
from the plan. The guides carry APA-style templates (`references/statistical-analysis/references/reporting_standards.md`)
and a sample-size justification template (`references/statistical-power.md`). Plots of
estimates go through `ggplot-visualization` or `python-visualization`.

## In Biorouter

- Run Python with the Developer shell in a project environment; the guides pin versions and
  ship runnable helpers (`references/statistical-analysis/scripts/assumption_checks.py`,
  `references/statistical-power/scripts/power.py`, `references/pymc/scripts/model_diagnostics.py`).
- When the person has an R session open and gptr Agent is installed, fit brms or lme4 models in
  that session instead of a fresh one; R code style follows `r-scripting`.
- Before results go into a manuscript, `claim-evidence-integrity` checks every number against
  its source output.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/statistical-analysis.md` | Test selection, assumption checks, effect sizes, Bayesian alternatives, APA reporting |
| `references/statistical-power.md` | Closed-form and simulation power, minimum detectable effects, sample-size justification |
| `references/statsmodels.md` | Linear models, GLMs, discrete choice, mixed models, time series, diagnostics |
| `references/pymc.md` | PyMC workflow, distributions, sampling and variational inference, diagnostics, LOO comparison |
| `references/r-bayes-brms.md` | brms formulas and priors, multilevel models, DAGs with dagitty, marginal effects, diagnostics |
