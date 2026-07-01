---
name: drug-discovery-benchmarks
description: Plan drug-discovery benchmark workflows with TDC-style datasets, ADMET, virtual screening, molecular property prediction, scaffold splits, leakage checks, and assay provenance. Use when evaluating compound models, benchmarks, or drug-discovery ML results.
user-invocable: true
license: Apache-2.0
---

# Drug Discovery Benchmarks

Source adaptation: BioRouter-original synthesis inspired by remaining Scientific Agent Skills and Auto-Empirical Research Skills capability clusters, rewritten under Apache-2.0. This is not copied upstream text; it is a native BioRouter routing and verification checklist.

## When to Use

Use this skill when the user asks about compound benchmarks, ADMET, virtual screening, scaffold splits, assay provenance, or drug-discovery ML. Prefer the most specific BioRouter extension, BioSkill, or language style skill whenever a concrete platform, package, or file type appears.

## Intake

Before producing output, capture:

- Research or operational question.
- Data, platform, package, or source material involved.
- Unit of analysis, model system, cohort, sample, or artifact.
- Desired deliverable: plan, code, review, table, figure, protocol, or narrative.
- Constraints: credentials, privacy, licensing, compute budget, validation standard, or external service availability.

## BioRouter Routes

Use these routes when applicable:

- Platform/API work: call the relevant BRXT extension first and keep mutation/execution gated.
- Biomedical or omics data: load the relevant `bio-skills` category.
- Statistical/causal claims: load `causal-identification-gates`, `statistical-modeling-bayes`, or `econometrics-toolkit`.
- Evidence/citations: load `citation-temporal-integrity` and `claim-evidence-integrity`.
- Reproducibility: load `replication-package-audit` before treating the result as final.

## Quality Gates

Do not present final claims until these are true:

1. Provenance is explicit: source files, APIs, ids, versions, dates, or citations.
2. The method matches the data-generating process and the intended claim.
3. Assumptions and failure modes are listed plainly.
4. Validation is tied to an actual benchmark, holdout, sensitivity check, audit trail, or source record.
5. The output can be rerun, reviewed, or traced by another person.
6. Anything requiring external credentials, proprietary data, wet-lab execution, or live services is marked unverified unless actually checked.

## Response Shape

Return:

- Recommended route.
- Minimal next action.
- Verification checklist.
- Risks or blockers.
- Exact artifact to produce next, if any.
