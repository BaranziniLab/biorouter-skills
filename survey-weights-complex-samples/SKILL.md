---
name: survey-weights-complex-samples
description: Analyse data from complex survey designs (NHANES, NHIS, BRFSS, ACS PUMS, CPS, DHS, IPUMS and institutional surveys) with design-based inference, setting up weights, strata, clusters (PSUs), finite population corrections and replicate weights, estimating means, proportions, totals and regressions for the whole population and subgroups, and building weights with nonresponse adjustment, raking and trimming. Use with R survey or srvyr, Python samplics, or Stata svy, whenever survey weights or a sampling design are involved.
user-invocable: true
license: Apache-2.0
metadata:
  version: "1.1.0"
  origin: native
  upstream: "none (native rewrite, no upstream text copied)"
---

# Survey Weights and Complex Samples

A national survey is not a simple random sample. Ignoring its weights biases estimates; ignoring
its strata and clusters makes standard errors too small, often by half. This skill sets up the
design correctly before any estimate. It is written for Biorouter and copies no upstream text.

## Find the design in the documentation

From the survey's own analytic guidelines, record:

- the **weight** for the analysis (and which one: interview, exam, fasting subsample, multi-cycle);
- the **strata** and **primary sampling unit (PSU)** variables, or the **replicate weights** and
  their method (BRR, Fay's BRR with its rho, jackknife JK1 or JKn, bootstrap) and scale factors;
- whether a **finite population correction** applies;
- how to **combine cycles or years** (for example NHANES: divide two-year weights by the number of
  cycles combined).

| Survey | Typical design variables |
| --- | --- |
| NHANES | `WTINT2YR`, `WTMEC2YR` or subsample weights; strata `SDMVSTRA`; PSU `SDMVPSU` |
| NHIS (2019 on) | `WTFA_A` (sample adult); strata `PSTRAT`; PSU `PPSU` |
| BRFSS | `_LLCPWT`; strata `_STSTR`; PSU `_PSU` |
| ACS PUMS | `PWGTP` or `WGTP` with 80 replicate weights (`PWGTP1` to `PWGTP80`), successive difference replication (variance factor 4/80) |
| CPS ASEC | Supplement weights with replicate weights; check the year's documentation |

Variable names change between releases; always confirm in that release's codebook.

## Set up the design, then estimate

R with `survey` (or the tidy `srvyr` interface):

```r
library(survey)
options(survey.lonely.psu = "adjust")   # strata with one PSU after subsetting
des <- svydesign(ids = ~SDMVPSU, strata = ~SDMVSTRA, weights = ~WTMEC2YR,
                 nest = TRUE, data = nhanes)
svymean(~bmi, des, na.rm = TRUE)
svyby(~diabetes, ~age_group, des, svymean, na.rm = TRUE)
fit <- svyglm(diabetes ~ age + sex + bmi, design = des, family = quasibinomial())
# replicate-weight surveys
rep <- svrepdesign(weights = ~PWGTP, repweights = "PWGTP[0-9]+", type = "successive-difference",
                   mse = TRUE, data = pums)
```

Python with `samplics`:

```python
from samplics.estimation import TaylorEstimator
from samplics.utils.types import PopParam     # older releases take the string "mean" instead
est = TaylorEstimator(PopParam.mean)
est.estimate(y=df["bmi"], samp_weight=df["WTMEC2YR"], stratum=df["SDMVSTRA"],
             psu=df["SDMVPSU"], remove_nan=True)
```

Stata: `svyset SDMVPSU [pweight=WTMEC2YR], strata(SDMVSTRA) vce(linearized)` then `svy:`
prefixes; `svy, subpop(...)` for subgroups.

## Rules that prevent the common errors

1. **Subgroups through the design, never by subsetting the data first.** Use `subset()` on the
   design object in R, `subpop()` in Stata, or the domain argument in samplics. Dropping rows
   before declaring the design removes PSUs and understates variance.
2. **Use the right weight for the variables in the model.** Variables from an exam or lab
   subsample need that subsample's weight; mixing in interview-only variables does not change
   that.
3. **Report unweighted counts with weighted estimates.** Suppress or flag estimates from small
   cells or with a large relative standard error (many agencies flag above 30%).
4. **Design effects tell you what you have.** Report the effective sample size or design effect
   when planning or interpreting precision.
5. **Regression with weights is design-based inference.** Use `svyglm` or `svy:` models, not
   `glm(weights = )`, which treats weights as frequency or precision weights and gets the
   standard errors wrong. Use quasi-binomial or quasi-Poisson families for binary and count
   outcomes in `svyglm`.
6. **Missing data**: weighting does not fix item nonresponse. Impute within the design
   (`mitools` with `survey`, or `svy` with `mi estimate`) and combine with Rubin's rules.
7. **Combine cycles correctly**, keeping strata and PSUs distinct across cycles as the survey
   documents.

## Building weights for your own survey

When the person ran the survey: start from base weights (inverse selection probabilities), adjust
for nonresponse within cells or with response-propensity models, then calibrate to known
population margins by raking (`survey::rake`, `survey::calibrate`, `samplics` calibration, Stata
`ipfraking`). Trim extreme weights with a documented rule and recalibrate. Report the weighting
steps, the margins and their source, and the resulting design effect from unequal weighting
(Kish's 1 + CV squared).

## Reporting

State the survey, release and years; the weight, strata, PSU or replicate method; how subgroups
were defined; the variance method (Taylor linearisation or replication); software and version;
and both unweighted n and weighted estimates with 95% confidence intervals. Cite the survey as its
documentation requires (IPUMS, for example, requires a specific citation).

## Related skills

- `statistical-modeling-bayes` for model-based analysis of non-survey data, and for multilevel
  regression and poststratification (MRP) when small-area estimates are needed.
- `psychometrics-sem-measurement` for scales measured in surveys (lavaan accepts sampling weights
  and clusters through `lavaan.survey` or its own `sampling.weights` and `cluster` arguments).
- `econometrics-toolkit` for IPUMS, CPS or ACS microdata in policy designs.
- When gptr Agent is installed, run `survey` models in the person's live R session.
