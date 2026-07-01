---
name: general-time-series-forecasting
description: Plan and review general time-series forecasting with classical models, ML, foundation models, backtesting, leakage checks, and uncertainty. Use for non-omics forecasting, sensor streams, operations, finance, clinical vitals, demand, or irregular temporal data.
user-invocable: true
license: Apache-2.0
---

# General Time-Series Forecasting

Source adaptation: BioRouter-original synthesis inspired by Scientific Agent Skills time-series and forecasting patterns, rewritten under Apache-2.0.

## When to Use

Use this skill for general forecasting or temporal prediction outside BioRouter's omics-specific `temporal-genomics` BioSkills. Use it for sensors, operations, finance, clinical vitals, weather, demand, events, or multivariate temporal panels.

## Intake

Collect:

- Forecast target, horizon, cadence, and decision use.
- Entity structure: single series, panel, hierarchy, spatial-temporal, or event stream.
- Exogenous covariates and when they are known.
- Missingness, irregular sampling, seasonality, interventions, and regime changes.
- Train/validation/test dates and backtesting expectations.
- Required uncertainty: intervals, quantiles, scenarios, or calibrated probabilities.

## Model Routing

- Baseline first: seasonal naive, moving average, ETS, ARIMA/SARIMA, or Prophet-style decompositions.
- Use ML when feature history and panel size justify it: gradient boosting, random forests, neural nets.
- Use deep/foundation models only after checking horizon, frequency, scaling, covariate availability, and license.
- Use causal methods when the task asks about interventions, not just forecasts.
- Use `financial-accounting-econometrics` for market/event-study tasks and `clinical-decision-support-review` for patient-impacting forecasts.

## Backtesting Gates

1. Use time-ordered splits only.
2. Prevent leakage from future covariates, normalization, target encoding, or imputation.
3. Compare against simple baselines.
4. Report horizon-specific metrics.
5. Check calibration if intervals or probabilities are reported.
6. Preserve timestamp timezone, calendar, and missingness decisions.

## Output Shape

Return:

- Forecast framing.
- Baseline and candidate models.
- Backtest plan.
- Leakage checklist.
- Metrics and uncertainty plan.
- Minimal reproducible code or commands if requested.
