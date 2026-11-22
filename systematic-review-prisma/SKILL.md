---
name: systematic-review-prisma
description: Run a systematic, scoping or rapid review and meta-analysis end to end, from protocol (PICO, PROSPERO) and reproducible database searches through dual screening, data extraction, risk of bias and GRADE to pooling effect sizes (random effects, diagnostic accuracy bivariate and HSROC, Bayesian and network meta-analysis), heterogeneity, small-study bias, forest and funnel plots, and PRISMA 2020 reporting. Use for any literature review that must be reproducible, or whenever study results need to be combined (meta-analysis).
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/literature-review); Aperivue/medsci-skills@7e9d133dd0216c29b0e030729e3719c3db5e0973 (skills/meta-analysis); choxos/BiostatAgent@a55c0591107181cdac9ce78813dc0abac3281caa (plugins/r-tidy-modeling/skills/meta-analysis, plugins/bayesian-modeling/skills/meta-analysis)"
---

# Systematic Review and Meta-analysis

A review is systematic when someone else could rerun it and get the same set of studies. This
skill keeps every step logged, from the search string to the pooled estimate, and keeps records,
reports and studies apart. It also pools effect sizes, which no other BAAM skill does. The four
guides under `references/` come from K-Dense Scientific Agent Skills, Aperivue medsci-skills and
choxos BiostatAgent (MIT; see `LICENSE-UPSTREAM`). This skill was called "Systematic Review and
PRISMA" before version 1.1.0.

## Pick the review type first

| Type | Use when | Output |
| --- | --- | --- |
| Systematic review with meta-analysis | A focused question (PICO or PIRD for diagnostic accuracy) and comparable quantitative results | Pooled estimates, heterogeneity, certainty (GRADE), PRISMA 2020 |
| Systematic review without meta-analysis | Studies too different to pool | Structured synthesis (SWiM guideline), tables, certainty |
| Scoping review | Mapping what exists, concepts or evidence gaps | Evidence map, PRISMA-ScR |
| Rapid or narrative review | Time-limited or background synthesis | Clearly labelled shortcuts; never called systematic |

## Workflow and where each step lives

| Phase | What happens | Guide |
| --- | --- | --- |
| 1. Protocol | Question, eligibility criteria, outcomes and effect measures, planned analyses; register on PROSPERO or OSF before screening | `references/meta-analysis-pipeline.md`, `references/meta-analysis-pipeline/references/PROSPERO_template.md` |
| 2. Search | Database-specific strings (PubMed, Embase, CENTRAL, Web of Science, Scopus, preprint servers), dates and hit counts logged, de-duplication | `references/literature-review.md`, `references/literature-review/references/database_strategies.md` |
| 3. Screening | Title and abstract, then full text, by two reviewers independently; disagreements resolved and kappa reported; reasons for each full-text exclusion | `references/meta-analysis-pipeline/references/phase3_screening_detail.md` |
| 4. Extraction | Piloted form, two extractors, source page and quote for each number, cohort-overlap check | `references/meta-analysis-pipeline/references/phase4_extraction_detail.md` |
| 5. Risk of bias | RoB 2 for randomised trials, ROBINS-I for non-randomised studies, QUADAS for diagnostic accuracy, PROBAST for prediction models, each from its official publication | `references/meta-analysis-pipeline.md` |
| 6. Synthesis | Effect sizes, pooling, heterogeneity, subgroups and meta-regression, small-study bias, sensitivity | `references/meta-analysis-r.md`, `references/meta-analysis-bayesian.md`, `references/meta-analysis-pipeline/references/phase6_statistical_synthesis.md` |
| 7. Certainty | GRADE per outcome, with reasons for each downgrade | `references/meta-analysis-pipeline.md` |
| 8. Reporting | PRISMA 2020 flow diagram and checklist (PRISMA-DTA, PRISMA-ScR as needed), protocol deviations | `references/literature-review.md`, `references/meta-analysis-pipeline.md` |

## Pooling: decisions to make explicitly

- **Effect measure** fixed in the protocol: mean difference or standardised mean difference
  (Hedges' g), risk ratio or odds ratio, hazard ratio on the log scale, correlation via Fisher's
  z, sensitivity and specificity for diagnostic accuracy.
- **Model**: random effects by default when studies differ in populations or methods. Estimate
  between-study variance with REML or Paule-Mandel, not DerSimonian-Laird alone, and use the
  Hartung-Knapp adjustment when there are few studies. Report tau-squared and a prediction
  interval, not only I-squared.
- **Diagnostic accuracy**: pool sensitivity and specificity jointly (bivariate model or HSROC);
  never pool them separately.
- **Small numbers**: with fewer than about five studies, random-effects estimates of
  heterogeneity are unstable; a Bayesian model with a weakly informative prior on tau (see
  `references/meta-analysis-bayesian.md`) or a narrative synthesis may be more honest.
- **Small-study effects**: funnel plots and Egger's test need about ten or more studies; treat
  trim-and-fill as a sensitivity analysis, not a correction.
- **Network meta-analysis** needs connected networks and checks of consistency between direct
  and indirect evidence; the Bayesian guide covers the model.
- **Units and overlap**: one estimate per independent cohort; detect overlapping cohorts before
  pooling (`references/meta-analysis-pipeline/scripts/cohort_overlap_check.py`).

## Integrity checks before reporting

1. The PRISMA counts reconcile: records identified, after de-duplication, screened, excluded,
   reports sought and retrieved, assessed and included, studies included
   (`references/meta-analysis-pipeline/scripts/prisma_5way_consistency.py`).
2. Every pooled input traces to an extraction row with a source page, and every number in the
   manuscript traces to the analysis output (`references/meta-analysis-pipeline/scripts/check_pool_consistency.py`).
3. Ratio estimates and their intervals are symmetric on the log scale
   (`references/meta-analysis-pipeline/scripts/check_ratio_ci_symmetry.py`).
4. Every reference resolves in a registry (`citation-library-management`), and each claim in the
   text is supported (`claim-evidence-integrity`).

AI assistance in screening or extraction is a suggestion for a human reviewer, logged as such;
it never replaces the second reviewer.

## Notes on the adapted guides

- The medsci-skills guide names commands from its own project. In Biorouter, use: topic
  scouting (`/ma-scout`) through LiteratureAgent searches; statistics (`/analyze-stats`) through
  the `clinical-biostatistics` bundle or `statistical-modeling-bayes`; figures (`/make-figures`)
  through `ggplot-visualization`; reporting checks (`/check-reporting`) through
  `replication-package-audit`; manuscript drafting (`/write-paper`) through
  `scientific-manuscript-writing`.
- Files inside `references/meta-analysis-pipeline/` that mention `${CLAUDE_SKILL_DIR}` mean
  that folder.
- The upstream risk-of-bias checklist summaries are not bundled; use each tool's official
  publication and forms.

## In Biorouter

- LiteratureAgent searches OpenAlex, Crossref, PubMed, Semantic Scholar, bioRxiv and Unpaywall;
  BioMCPAgent, when installed, adds PubMed, Europe PMC and ClinicalTrials.gov queries. Log every
  query string, date and count either way.
- Run R meta-analysis (`meta`, `metafor`, `mada`, `brms`) with the Developer shell, or in the
  person's open R session through gptr Agent.
- `scientific-research` orchestrates a broader research question and calls this skill for the
  review itself.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/literature-review.md` | Review types, search strategy, records versus reports versus studies, screening, synthesis, PRISMA figures, citation checks, PDF export |
| `references/meta-analysis-pipeline.md` | End-to-end protocol to manuscript pipeline: screening reconciliation, extraction, risk of bias, synthesis, GRADE, reporting, audits |
| `references/meta-analysis-r.md` | Effect sizes, fixed and random effects with meta and metafor, heterogeneity, forest and funnel plots, bias tests, subgroups, meta-regression |
| `references/meta-analysis-bayesian.md` | Bayesian fixed, random-effects and network meta-analysis in Stan and JAGS, priors for heterogeneity, publication-bias models |
