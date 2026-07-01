---
name: psychometrics-sem-measurement
description: Plan measurement workflows: scale reliability, CFA/SEM, mediation/moderation, latent constructs, invariance, item analysis, and APA-style reporting. Use for surveys, instruments, behavioral measures, or psychometric validation.
user-invocable: true
license: Apache-2.0
---

# Psychometrics, SEM, and Measurement

Source adaptation: BioRouter-original synthesis inspired by Auto-Empirical Research Skills capability clusters, rewritten under Apache-2.0. This is native BioRouter guidance and does not copy upstream text.

## When to Use

Use this skill when the user asks about scale reliability, CFA, SEM, measurement invariance, mediation, moderation, latent constructs, or psychometric reporting. If the task is biomedical, clinical, or omics-specific, combine this with the appropriate BioSkills category and extension instead of treating the methods in isolation.

## Intake

Collect:

- Research question, estimand, and audience.
- Dataset/source, file formats, licenses, access constraints, and identifiers.
- Unit of analysis, time period, sample design, and outcome/treatment definitions.
- Software stack and expected artifact: code, table, figure, memo, manuscript, appendix, or review response.
- Whether the work is exploratory, confirmatory, replication, submission, or referee-response.

## Method Gates

Before writing conclusions:

1. State the design and estimand before the model.
2. Preserve provenance for every dataset, variable, citation, and transformation.
3. Match inference to the sampling/assignment structure.
4. Identify weights, clusters, panels, repeated measures, or dependence before estimating.
5. Check robustness against the actual design threat, not decorative alternative models.
6. Keep code/table/figure outputs reproducible from a clean entry point.

## BioRouter Routing

- Use `empirical-research-router` for full workflow staging.
- Use `causal-identification-gates` before causal language.
- Use `econometrics-toolkit`, `statistical-modeling-bayes`, or `financial-accounting-econometrics` for adjacent method detail.
- Use `citation-temporal-integrity`, `claim-evidence-integrity`, and `replication-package-audit` for publication-facing outputs.

## Output Pattern

Return a compact plan with:

- Primary route and why.
- Required data/design evidence.
- Minimal next command or artifact.
- Failure modes.
- Verification checklist before final claims.
