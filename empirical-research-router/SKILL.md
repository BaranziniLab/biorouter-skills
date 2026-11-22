---
name: empirical-research-router
description: "Analysis-stage router for empirical research, called by scientific-research once a question needs data analysis, or used directly for an analysis: routes through question framing, design register, data audit, identification strategy, estimation, robustness, replication package and reporting. Use when a user asks for applied statistics, causal inference, econometrics, epidemiology or social-science style empirical analysis rather than one isolated command."
user-invocable: true
license: Apache-2.0
metadata:
  version: "1.1.0"
  origin: native
  upstream: "none (native rewrite, no upstream text copied)"
---

# Empirical Research Router

Source adaptation: Biorouter-original synthesis from ideas in the Auto-Empirical Research Skills workflow patterns, rewritten under Apache-2.0; no upstream text is copied (that project is CC BY-SA 4.0).

Use this skill as the analysis-stage controller for empirical research. Its job is to choose the right downstream skill, define the evidence required before claims are made, and stop the agent from jumping from a dataset to a polished conclusion without a design audit.

## Layering

- `scientific-research` owns a whole research question: scoping, literature, hypotheses, the analysis plan and the cited draft. When its work reaches the point where data must be analysed, it calls this skill. This skill owns that analysis stage and hands its stage passport back.
- Called directly, this skill runs the analysis stage only. If the request also needs a literature review, hypothesis generation or a full written paper, load `scientific-research` and let it call this skill for the analysis.
- `science-superpowers`, when installed, supplies general scientific method gates (hypothesis, controls, pre-registration). Use them inside a stage; this skill keeps the empirical stage register and the routing.

## Intake

Before analysis, collect:

- Research question and target audience.
- Unit of analysis, population, time window, and outcome.
- Treatment/exposure/predictor definition.
- Data source, access constraints, and whether data are observational, randomized, quasi-experimental, or descriptive.
- Deliverable: analysis plan, code, robustness memo, manuscript section, replication package, or review.

If the user asks for biomedical or omics work, route to the matching Biomedical bundle (for example `clinical-biostatistics`, `single-cell` or `differential-expression`) first. If the request is about empirical causal inference, route to `causal-identification-gates` before estimating anything.

## Stage Passport

Maintain a short stage passport in the response or project notes:

| Stage | Required evidence |
|---|---|
| Scope | One-sentence question, estimand, population, unit, outcome |
| Design | Identification strategy, assumptions, alternative designs rejected |
| Data | Sample construction, exclusions, missingness, provenance |
| Variables | Treatment, outcome, covariates, mediators, colliders, timing |
| Estimation | Primary estimator, inference strategy, clustering level |
| Robustness | Sensitivity checks tied to design risks |
| Claims | Claim-evidence map, limits, unverified items |
| Reproducibility | Master script, relative paths, seeds, session info |

Do not advance to reporting until the stage passport has no fatal gaps.

## Routing

- Causal design: load `causal-identification-gates`.
- Clinical outcomes: load the `clinical-biostatistics` bundle plus causal gates if observational.
- Machine learning causal effects or CATE: load the `machine-learning` bundle's `causal-ml-dml`, or `causal-heterogeneity-policy-learning` for policy learning.
- Literature and citation grounding: load `claim-evidence-integrity` (it now holds the citation and temporal checks) and the `database-access` bundle's `open-literature-discovery`; for a systematic search or meta-analysis, load `systematic-review-prisma`.
- Manuscript consistency: load `claim-evidence-integrity`.
- Reproducibility: load `replication-package-audit`.

## Method Gate

Before accepting results as research evidence, require:

1. The estimand is stated before the model.
2. The design matches the data-generating setting.
3. Bad controls, mediators, and colliders are identified.
4. Standard errors match the assignment/sampling structure.
5. Robustness checks test real threats, not decorative alternatives.
6. The result can be reproduced from a clean entry point.

If any item fails, report the gap and propose the next concrete check instead of writing a conclusion.
