---
name: clinical-decision-support-review
description: Prepare and check research documentation for clinical decision support, treatment plans and clinical reports, including GRADE evidence profiles, aggregate cohort and model evaluation tables, decision-logic traceability, clinician-authored treatment-plan records, case, diagnostic and trial report scaffolds, de-identification checks and governance notes. Use with de-identified, synthetic or aggregate data for research, quality improvement or regulatory documentation, never for deciding a real patient's care.
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/clinical-decision-support, skills/treatment-plans, skills/clinical-reports)"
---

# Clinical Decision Support Review

This skill structures and checks the documents that surround clinical decision support in
research: what the evidence says, how a rule or model performs on a cohort, how a decision was
recorded, and how a report traces back to verified facts. The three guides under `references/`
are adapted from K-Dense Scientific Agent Skills (MIT; see `LICENSE-UPSTREAM`); each ships
templates and local, network-free checkers.

## Hard boundary

- **No clinical decisions.** Do not recommend, rank or change treatment for a real patient, and
  do not interpret an individual's results for care. Treatment-plan work transcribes decisions
  that licensed clinicians already made and verified; it never infers them.
- **No identifiable data in this workflow** unless the person confirms it is approved for this
  environment. Prefer aggregate, synthetic or de-identified inputs. Small cells (counts below
  the threshold the institution sets, often 11) are suppressed in any output.
- **Every artefact is a draft for qualified review.** Outputs carry the intended-use header the
  guides define and are released only after a named reviewer signs off.

## Choose the artefact

| Need | Artefact | Guide |
| --- | --- | --- |
| Summarise the evidence for a recommendation | GRADE evidence profile with certainty per outcome | `references/clinical-decision-support.md` |
| Describe a cohort or compare groups | Aggregate cohort table (Table 1) with suppression | `references/clinical-decision-support/references/cohort_evaluation.md` |
| Evaluate a rule, score, biomarker or model | Aggregate performance (discrimination, calibration, decision curves) with intended use | `references/clinical-decision-support/references/model_biomarker_evaluation.md` |
| Document how a rule maps inputs to recommendations | Decision-logic traceability record | `references/clinical-decision-support/references/decision_logic_traceability.md` |
| Plan survival or time-to-event evaluation | Survival analysis plan | `references/clinical-decision-support.md` |
| Record a clinician-authored treatment plan for research or a handoff | Treatment-plan package with source-fact manifest, goals and checkpoints, shared decision record | `references/treatment-plans.md` |
| Draft a case report, diagnostic report scaffold, trial results or safety summary | Report template plus source-fact manifest and consistency checks | `references/clinical-reports.md` |

## Workflow

1. **State intended use and audience**: research publication, internal quality improvement,
   regulatory submission or teaching. This picks the reporting guideline (CARE for case
   reports, STARD for diagnostic accuracy, TRIPOD+AI for prediction models, CONSORT for
   trials, DECIDE-AI for early clinical evaluation of AI) and the governance path.
2. **Confirm the data gate**: what data, from where, under which approval (IRB, QI
   determination, data use agreement), and its de-identification status.
3. **Build a source-fact manifest**: every number and statement in the artefact points to a
   verified source (an analysis output file, a guideline section, a clinician's record).
4. **Generate the template** from the guide's assets and fill only verified fields; leave the
   rest visibly empty.
5. **Run the local checkers** the guide provides (completeness, traceability, consistency,
   de-identification); fix every failure.
6. **Human review and release** by a qualified person, recorded in the artefact.

## Evaluation of a rule or model

Report discrimination (AUROC with interval), calibration (calibration plot, slope and
intercept), and clinical usefulness (decision curve analysis or net benefit at clinically
chosen thresholds), overall and in subgroups where performance could differ (sex, age, race and
ethnicity, site). Say which population the evaluation covers and how it differs from where the
tool would be used. Model building itself belongs to `clinical-ai-modeling`; statistics of
effects and trials to the `clinical-biostatistics` bundle.

## In Biorouter

- Aggregate cohort counts from UCSF data can come from UCSFOMOPAgent or CDWAgent in a private
  chat; keep row-level extracts inside the approved environment and bring only aggregate tables
  into this workflow.
- Run the guides' checkers with the Developer shell; they use only the Python standard library
  and touch only local files (`references/clinical-decision-support/scripts/`,
  `references/treatment-plans/scripts/`, `references/clinical-reports/scripts/`).
- Evidence synthesis behind a GRADE profile: `systematic-review-prisma`. Claims in the final
  document: `claim-evidence-integrity`. Device and laboratory quality systems:
  `regulatory-quality-systems`.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/clinical-decision-support.md` | Safety boundary, data gate, GRADE profiles, cohort tables, model and biomarker evaluation, survival plans, decision logic, privacy, reporting guidelines, governance |
| `references/treatment-plans.md` | Transcribing verified clinician decisions, source ledger, goals and checkpoints, shared decisions, reconciliation handoffs, release gates |
| `references/clinical-reports.md` | Case, diagnostic, trial and safety report scaffolds, source-fact manifests, de-identification, consistency checks, review routing |
