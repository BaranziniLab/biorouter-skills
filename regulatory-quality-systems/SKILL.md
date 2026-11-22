---
name: regulatory-quality-systems
description: Prepare readiness evidence for quality-management and laboratory-competence standards (ISO 13485 medical device QMS, ISO 14971 risk management, ISO/IEC 17025 testing and calibration labs, ISO 15189 medical labs, FDA QMSR transition), and plan, evaluate and document analytical method validation, verification and transfer under ICH Q2(R2) and Q14, USP 1225 and 1226, ICH M10 bioanalytical, CLSI EP guidelines or ISO 17025. Use for document control, CAPA, risk files, scope of accreditation, accuracy, precision, linearity, LOD and LOQ, or method comparison.
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/iso-standards-readiness, skills/analytical-method-validation)"
---

# Regulatory and Quality Systems

Quality work is evidence work: a procedure is compliant when records show it was followed, and
a method is validated when data show it fits its intended use. This skill organises that evidence
and runs the arithmetic, with the two guides under `references/` adapted from K-Dense Scientific
Agent Skills (MIT; see `LICENSE-UPSTREAM`).

## Boundaries

- **Readiness is not certification.** Only an accredited certification body or accreditation
  body (and, for devices, the regulator) decides conformity. Outputs here are internal readiness
  reviews and drafts for the quality owner.
- **Standards are copyrighted.** Work from the organisation's licensed copies of ISO, IEC, ICH,
  USP and CLSI documents; do not ask for or reproduce their text. The guides paraphrase
  structure and point at clauses, not content.
- **Named owners decide.** The quality manager, laboratory director or management
  representative approves documents and accepts residual risk; this skill prepares the material.

## Choose the lane

| Question | Framework | Guide |
| --- | --- | --- |
| Is our medical device quality system ready for audit; does our document and record control work; what does the FDA QMSR change | ISO 13485, 21 CFR 820 (QMSR) | `references/iso-standards-readiness.md`, `references/iso-standards-readiness/references/iso-13485.md` |
| Is our risk management file complete and traceable | ISO 14971 with ISO/TR 24971 | `references/iso-standards-readiness/references/iso-14971.md` |
| Testing or calibration laboratory accreditation, scope, traceability, measurement uncertainty, proficiency testing | ISO/IEC 17025 | `references/iso-standards-readiness/references/iso-17025.md` |
| Medical (clinical) laboratory accreditation | ISO 15189 (with CAP or CLIA where they apply) | `references/iso-standards-readiness/references/iso-15189.md` |
| Is this analytical procedure fit for purpose: plan, evaluate and report a validation | ICH Q2(R2) and Q14, USP 1225 (validation) and 1226 (verification), CLSI EP series | `references/analytical-method-validation.md` |
| Bioanalytical method validation and study-sample runs (LC-MS/MS, ligand binding) | ICH M10 | `references/analytical-method-validation/references/ich-m10-bioanalytical.md` |
| Transfer a method between labs or compare two methods | USP 1224, CLSI EP09, Bland-Altman and Deming or Passing-Bablok regression | `references/analytical-method-validation.md` |

## Readiness workflow (management systems)

1. Declare the standard and edition, the scope (sites, products, tests), the purpose (gap
   assessment, internal audit, pre-assessment) and the owners.
2. Freeze the evidence: controlled document register with versions and approval dates, record
   samples, and the date of the review.
3. Inventory documents and records against the process map; find missing, obsolete and
   unapproved documents (`references/iso-standards-readiness/scripts/audit_document_records.py`).
4. Review implementation: are records complete, signed and dated; does CAPA close with
   effectiveness checks; do management reviews have their required inputs.
5. Check traceability where the lane needs it: requirements to risk controls to verification
   for devices (`references/iso-standards-readiness/scripts/check_traceability.py`); measurement
   traceability and uncertainty for laboratories.
6. Write a bounded readiness report: findings with evidence references, severity, owner and due
   date, and what was out of scope.

## Validation workflow (analytical methods)

1. **Fix the framework and the intended use first** (analyte, matrix, range, decision the
   result supports); it determines which characteristics are required and their acceptance
   criteria (`references/analytical-method-validation/scripts/plan_validation.py`).
2. **Write the protocol with criteria before any data** (template in
   `references/analytical-method-validation/assets/validation-protocol-template.md`).
3. **Evaluate response**: linearity and range from residuals and back-calculated
   concentrations, not from the correlation coefficient alone
   (`references/analytical-method-validation/scripts/check_response.py`).
4. **Accuracy and precision**: recovery or bias with intervals, repeatability and intermediate
   precision from a nested design (`check_accuracy_precision.py`).
5. **Detection and quantitation limits**: estimate, then confirm with samples near the limit
   (`check_detection_limits.py`).
6. **Report** results against every criterion, with deviations and their impact
   (`references/analytical-method-validation/assets/validation-report-template.md`).

A criterion chosen after seeing the data is not a criterion. Failed characteristics are
reported, investigated and either fixed with a protocol amendment or accepted with a documented
restriction of intended use.

## In Biorouter

- The guides' scripts run locally with the Python standard library and no network
  (`references/iso-standards-readiness/scripts/`, `references/analytical-method-validation/scripts/`).
- Measurement uncertainty budgets for ISO 17025 use `physical-science-computing`; statistical
  design of validation experiments uses `statistical-modeling-bayes`.
- Clinical documentation and governance around decision support belong to
  `clinical-decision-support-review`; research reproducibility to `replication-package-audit`.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/iso-standards-readiness.md` | Lanes for ISO 13485, 14971, 17025 and 15189, evidence architecture, document control, CAPA, supplier controls, QMSR transition, templates and checkers |
| `references/analytical-method-validation.md` | Framework selection, protocol and report templates, response, accuracy, precision, DL and QL, ICH M10 runs, transfer and method comparison, statistics |
