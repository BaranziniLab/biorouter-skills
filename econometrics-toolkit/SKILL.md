---
name: econometrics-toolkit
description: Estimate applied econometric models with the inference the design needs, in Python, R or Stata, covering OLS and GLMs with robust and clustered errors, panel fixed effects, difference in differences and staggered adoption, event studies, IV and 2SLS, regression discontinuity, synthetic control, finance and accounting event studies and factor models, reproducible Stata projects, and data sources such as WRDS, CRSP, Compustat, SEC EDGAR, FRED, Census and IPUMS. Use for panel or policy evaluation, clustered standard errors, Fama-MacBeth, CARs, or replicable Stata or fixest code.
user-invocable: true
license: Apache-2.0 AND BSD-3-Clause
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/statsmodels)"
---

# Econometrics Toolkit

This skill is the estimation stage of an applied econometrics project: it matches the estimator
and the standard errors to the design, writes code that reruns, and reports what the estimates
can and cannot say. The statsmodels guide under `references/` is adapted from K-Dense Scientific
Agent Skills (BSD-3-Clause; see `LICENSE-UPSTREAM`); everything else here is Biorouter-original.

It now contains three former skills as sections: **financial-accounting-econometrics**,
**stata-research-workbench** and **econ-finance-data-sources**. If one of those is also
installed, it is an earlier version of part of this skill and should yield to it.

## Before estimating

Run `causal-identification-gates` whenever the result will be read causally. Then write down:
the estimand (ATE, ATT, a dynamic effect at event time k, an elasticity), the unit and time
index, the level at which treatment is assigned, the comparison group, and the threats the
design must survive. `empirical-research-router` stages the whole project; this skill is one
stage of it.

## Choose the estimator

| Design | Estimator | Python | R | Stata |
| --- | --- | --- | --- | --- |
| Cross-section, linear | OLS with heteroskedasticity-robust or clustered errors | `statsmodels`, `pyfixest` | `fixest::feols` | `regress, vce(cluster)` |
| Panel with unit and time effects | Two-way fixed effects; high-dimensional fixed effects | `linearmodels.PanelOLS`, `pyfixest` | `fixest::feols(y ~ x \| id + t)` | `reghdfe` |
| Two-period, two-group policy change | Difference in differences | `pyfixest` | `fixest` | `reghdfe`, `didregress` |
| Staggered adoption, heterogeneous effects | Callaway and Sant'Anna; Sun and Abraham; de Chaisemartin and D'Haultfoeuille; Borusyak, Jaravel and Spiess imputation | `differences`, `pyfixest` (`did2s`, saturated event study) | `did`, `fixest::sunab`, `DIDmultiplegtDYN`, `didimputation` | `csdid`, `eventstudyinteract`, `did_multiplegt_dyn`, `did_imputation` |
| Endogenous regressor with an instrument | 2SLS or LIML, weak-instrument-robust inference | `linearmodels.IV2SLS` | `fixest::feols(y ~ x \| fe \| d ~ z)`, `ivreg` | `ivreghdfe`, `ivreg2`, `weakiv` |
| Assignment by a cutoff | Local polynomial regression discontinuity | `rdrobust` | `rdrobust`, `rddensity` | `rdrobust`, `rddensity` |
| One or few treated units, long pre-period | Synthetic control, synthetic DiD | `pysyncon` | `augsynth`, `synthdid` | `synth`, `sdid` |
| Binary, count or trade-flow outcomes | Logit and probit with marginal effects; Poisson pseudo-maximum likelihood with fixed effects | `statsmodels`, `pyfixest.fepois` | `fixest::feglm`, `fepois` | `logit`, `probit`, `ppmlhdfe` |
| Macro or single-series time series | ARIMA, VAR, cointegration | `statsmodels.tsa` | `vars`, `urca` | `var`, `vec` |

For statsmodels models (OLS, GLM, discrete choice, mixed models, time series, diagnostics), the
detailed guide is `references/statsmodels.md`.

**Avoid plain two-way fixed effects with staggered timing** when effects may change over time or
differ across cohorts: already-treated units act as controls and can flip signs. Use one of the
heterogeneity-robust estimators above and show the TWFE result only for comparison.

## Inference rules

- **Cluster at the level of treatment assignment** (state for a state policy, firm for a firm
  event), not at the level of the observation. With two plausible levels, cluster on both or on
  the coarser one.
- **Few clusters** (roughly under 40, or few treated clusters): use the wild cluster bootstrap
  (`boottest` in Stata, `fwildclusterboot` in R, `wildboottest` in Python) and report it.
- **Serial correlation in panels**: clustering by unit handles it; Newey-West HAC errors are
  for single time series.
- **Spatial correlation**: Conley standard errors with a stated distance cutoff.
- **Weak instruments**: report the first stage and an effective F statistic (Montiel Olea and
  Pflueger), and use Anderson-Rubin confidence sets when instruments are not strong.
- **Event studies**: plot pre-period coefficients with intervals, state the reference period,
  and test sensitivity to parallel-trend violations (Rambachan and Roth, `HonestDiD`). Flat
  pre-trends are necessary, not sufficient.

## Finance and accounting

- **Announcement event studies.** Define the event date precisely (trading day of the
  announcement, after-hours rule), an estimation window that ends before the event (for example
  days -250 to -30), a model of normal returns (market model or a Fama-French factor model), and
  an event window. Report cumulative abnormal returns with a test robust to event-induced
  variance (Boehmer, Musumeci and Poulsen) and a non-parametric rank test; with clustered event
  dates, use calendar-time portfolios instead.
- **Long-horizon returns** (BHAR) are badly behaved; prefer calendar-time factor regressions.
- **Panels of firms and years**: cluster by firm and year (Petersen 2009). Fama-MacBeth
  regressions handle cross-sectional correlation but not persistent firm effects; use
  Newey-West on the time series of coefficients.
- **Factor data**: Kenneth French's data library for Fama-French factors; record the download
  date because the library revises history.
- **Biases to rule out**: look-ahead (accounting data used before its public filing date; lag
  Compustat by the filing lag or use point-in-time data), survivorship (include delisted firms
  and delisting returns in CRSP), and outliers (winsorise at stated percentiles, per year).

## Data sources

| Source | What it holds | Access notes |
| --- | --- | --- |
| WRDS: CRSP, Compustat, IBES, TAQ, Audit Analytics | Prices and returns, fundamentals, analyst forecasts, trades | Institutional licence; `wrds` Python package or the web query tool; extracts must not be shared outside the licence. Merge CRSP and Compustat with the CCM link table, respecting link dates |
| SEC EDGAR | 10-K, 10-Q, 8-K filings and XBRL financial data | Free; the SEC asks automated clients to send a descriptive User-Agent with a contact the person provides, and to stay under 10 requests per second |
| FRED and ALFRED | US macro series, with vintages in ALFRED | Free API key; use vintages for real-time analysis |
| BLS, BEA, Census (ACS, CPS) | Labour, prices, national accounts, demographics | Public APIs; record table ids and release dates |
| IPUMS | Harmonised census and survey microdata | Registration, terms of use and a required citation; survey weights apply (`survey-weights-complex-samples`) |
| World Bank WDI, IMF, OECD | Cross-country indicators | Public APIs; series definitions change, record series codes |

For every source record the query, the extraction date and the version or vintage, and keep
raw extracts read-only.

## Reproducible Stata projects

- One master do-file runs everything from raw data to tables: `version 18` (or the version
  used) at the top, `set seed` before anything random, paths from one global set at the top,
  never `cd` to absolute paths scattered through files.
- Log every run (`log using logs/master.log, replace text`) and run non-interactively for the
  record (`stata-mp -b do master.do`).
- Vendor community packages into the project (`net install ... , from(local folder)` or a
  project `ado` directory added with `adopath ++`), because `ssc install` fetches whatever is
  current.
- Check data as you go: `isid` for keys, `merge ... , assert(match)` or explicit handling of
  unmatched rows, `assert` for ranges, `duplicates report`.
- Export tables from code (`esttab`, `etable`, `collect`), never by hand.
- The same structure applies to R (`fixest` plus `modelsummary`) and Python (`pyfixest` plus a
  table writer); `replication-package-audit` checks the result.

## Reporting

State the estimator, fixed effects, clustering level and number of clusters, sample and its
construction, and the robustness checks that address the main threats. Tables carry the
standard error type in a note. Results go to `claim-evidence-integrity` before they enter a
manuscript, and the submission and revision round to `empirical-paper-submission-rr`.

## Related skills

- `causal-identification-gates`, `empirical-research-router`, `empirical-benchmark-harness`.
- `causal-heterogeneity-policy-learning` for conditional effects and policy rules.
- `statistical-modeling-bayes` for general model choice; `survey-weights-complex-samples` for
  survey microdata; `general-time-series-forecasting` for forecasting.
- When gptr Agent is installed, run R estimates in the person's live R session.

## Guide in this skill

| Guide | Covers |
| --- | --- |
| `references/statsmodels.md` | Linear models, GLMs, discrete choice, mixed models, time series, diagnostics, model selection, common workflows |
