---
name: empirical-research-router
description: "Route empirical research requests through scoped stages: question framing, design register, data audit, identification strategy, estimation, robustness, replication package, and manuscript-ready reporting. Use when a user asks for applied statistics, causal inference, econometrics, epidemiology, social-science style empirical analysis, or a full research workflow rather than one isolated command."
user-invocable: true
license: Apache-2.0
---

# Empirical Research Router

Source adaptation: BioRouter-original synthesis from the Auto-Empirical Research Skills workflow patterns, rewritten for BioRouter under Apache-2.0. Do not copy upstream text into deliverables; use this as a native BioRouter operating checklist.

Use this skill as the top-level controller for empirical research. Its job is to choose the right downstream skill, define the evidence required before claims are made, and stop the agent from jumping from a dataset to a polished conclusion without a design audit.

## Intake

Before analysis, collect:

- Research question and target audience.
- Unit of analysis, population, time window, and outcome.
- Treatment/exposure/predictor definition.
- Data source, access constraints, and whether data are observational, randomized, quasi-experimental, or descriptive.
- Deliverable: analysis plan, code, robustness memo, manuscript section, replication package, or review.

If the user asks for biomedical or omics work, route to BioSkills first. If the request is about empirical causal inference, route to `causal-identification-gates` before estimating anything.

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
- Clinical outcomes: load `bio-skills/clinical-biostatistics/*` plus causal gates if observational.
- Machine learning causal effects or CATE: load `bio-skills/machine-learning/causal-ml-dml`.
- Literature and citation grounding: load `citation-temporal-integrity` and `bio-skills/database-access/open-literature-discovery`.
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
