---
name: clinical-ai-modeling
description: Plan and review clinical AI modeling workflows with EHR cohorts, PyHealth-style tasks, validation, bias checks, calibration, safety boundaries, and no-PHI handling. Use when users ask about clinical prediction models, risk scores, treatment-response ML, medical reports, or clinical model evaluation.
user-invocable: true
license: Apache-2.0
---

# Clinical AI Modeling

Source adaptation: BioRouter-original synthesis inspired by Scientific Agent Skills clinical AI patterns, rewritten under Apache-2.0.

## When to Use

Use this skill for clinical prediction, risk modeling, treatment-response modeling, EHR ML, report-generation evaluation, and clinical AI validation. Use `clinical-decision-support-review` when the output is a care recommendation or CDS text; use this skill when the core work is model design/evaluation.

## Intake

Collect:

- Clinical task: diagnosis, prognosis, readmission, mortality, treatment response, phenotyping, summarization, or triage.
- Cohort definition, index time, prediction time, horizon, and outcome definition.
- Data source: OMOP, FHIR, CDW, claims, notes, imaging, labs, vitals, medications, or multimodal data.
- De-identification/PHI constraints.
- Model type and evaluation target.
- Deployment status: research prototype, retrospective validation, prospective validation, or operational CDS.

## Cohort and Label Gates

1. Define index time before features.
2. Prevent label leakage from future notes, orders, procedures, outcomes, or discharge artifacts.
3. Capture inclusion/exclusion criteria and censoring.
4. Preserve code sets and vocabulary versions.
5. Separate development, validation, and external test cohorts.

## Evaluation Gates

- Discrimination: AUROC/AUPRC where appropriate.
- Calibration: reliability curve, calibration slope/intercept, Brier score.
- Clinical utility: decision curves or threshold-specific confusion matrices.
- Fairness/subgroups: site, race/ethnicity, sex/gender, age, insurance, language, and disease severity where available.
- Robustness: temporal validation, site validation, missingness stress tests.
- Explainability: use only as supporting evidence, not proof of safety.

## BioRouter Routes

- Use `CDWAgent`, `UCSFOMOPAgent`, or other BRXT extensions for authenticated data access.
- Use `causal-identification-gates` when causal treatment language appears.
- Use `statistical-modeling-bayes` for uncertainty and hierarchical validation.
- Use `claim-evidence-integrity` for manuscripts or model cards.
- Use `regulatory-quality-systems` for SaMD, design controls, or audit readiness.

## Safety Boundaries

Never present an unvalidated model as clinical advice. Mark research-only outputs clearly unless prospective validation, governance, monitoring, and deployment controls are documented.

## Output Shape

Return: task framing, cohort/label definition, model plan, leakage checks, evaluation table, subgroup plan, deployment/safety status, and open validation gaps.
