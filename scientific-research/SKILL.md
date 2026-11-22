---
name: scientific-research
description: "Run a research question end to end: scoping, literature review, hypothesis generation, analysis planning, result verification and a cited write-up. Use when the user wants to investigate a topic, survey prior work, plan or critique an analysis, draft a paper section, or run a multi-step 'do the research for me' task. Orchestrates; calls empirical-research-router for the analysis stage, claim-evidence-integrity for verification and scientific-manuscript-writing for drafting, and delegates data access to installed extensions (LiteratureAgent, BioMCPAgent, SPOKEAgent, CDWAgent, UCSFOMOPAgent)."
license: Apache-2.0
user-invocable: true
metadata:
  version: "1.1.0"
  origin: lab
  upstream: "none (lab-original)"
---

# Scientific Research

A pipeline for taking a research question from a one-line prompt to a verified, cited draft — without inventing facts. This skill is the **orchestrator**: it decides the path, then hands the domain work to the right tool. It does not replace a scientist's judgment; every claim it surfaces is meant to be checked, and it flags where it is uncertain.

> **House rule: no fabrication.** Never invent a citation, a DOI, a statistic, or a result. If a fact cannot be grounded in a retrieved source or a real computation, say so explicitly. A hallucinated reference is worse than a missing one.

---

## When this fires

Ask for it by name (or let it load on its own) when the request is a *research task*, not a code task:

- "What's known about X?" / "Survey the literature on Y."
- "Generate hypotheses for why Z happens."
- "Plan an analysis to test this." / "Is this analysis sound?"
- "Draft the introduction / methods / discussion for this."
- "Do the background research and write it up."

If the request is purely "write this code" or "run this tool," defer to `python-scripting`, `r-scripting`, the matching Biomedical bundle, or the relevant extension instead.

**Layering.** This skill orchestrates the whole question. When a stage needs empirical data analysis (design register, identification, estimation, robustness), it calls `empirical-research-router`, which owns that analysis stage and reports back through its stage passport. If `science-superpowers` is installed, use its method gates (hypothesis, controls, pre-registration, adversarial review) inside stages 3 to 5; this skill still decides the path.

The skills and extensions named below are BAAM items. Use the ones that are installed; when one that would clearly help is missing, say which one and that it can be added from BAAM (Skills or Extensions, Browse), and carry on with what is available.

---

## The loop

Run only the stages the task needs. Most requests need 2–4 of these, not all six.

### 1. Scope
Restate the question in one sentence. Name the deliverable (a survey? a hypothesis list? a methods paragraph?), the audience, and the stop condition. List what you already know vs. what you must retrieve. Surface ambiguities to the user *before* spending effort — a wrong scope wastes every later stage.

### 2. Literature review
Retrieve real sources; never recall them from memory.
- **Scholarly search:** use the **LiteratureAgent** extension (PubMed, OpenAlex, Crossref, Semantic Scholar) for searching and fetching records, and the **BioMCPAgent** extension for PubMed, Europe PMC and PubTator together with gene, variant and trial records (ClinicalTrials.gov, ClinVar, MyVariant). The `database-access` and `clinical-databases` Biomedical bundles hold the query methods for the same sources.
- **Knowledge graphs:** **SPOKEAgent** for gene, disease and drug relationships; **PrimeKGAgent** for PrimeKG. **MedCP**, if installed, also gives clinical-record and knowledge-graph queries.
- **Systematic search or meta-analysis:** load `systematic-review-prisma`, which owns the protocol, screening, PRISMA flow and pooled estimates.
- **The open web:** the **ScientificWebResearchAgent** extension, or whatever web-search tool Biorouter exposes.
- **Reference libraries:** the **ZoteroAgent** extension, and `citation-library-management` for library hygiene.
- For every source, capture: title, authors, year, venue, and a stable ID (DOI / PMID / arXiv). Drop anything you cannot resolve to a real identifier.
- Summarize per-source, then synthesize across sources. Note agreements, contradictions, and gaps — the gaps often *are* the contribution.

### 3. Hypothesis generation
From the synthesis, propose testable hypotheses. For each: state the mechanism, the prediction, and what evidence would confirm or refute it. Rank by novelty × testability. Mark which are already settled in the literature (don't re-propose known results).

### 4. Analysis planning
Translate a hypothesis into a concrete plan: data source, variables, model, assumptions, sample-size / power reasoning, confounders, and the pre-registered decision rule (what result means what *before* you look). For execution, hand off:
- empirical design, causal inference, econometrics → `empirical-research-router`;
- statistics & ML → the **clinical-biostatistics** / **machine-learning** Biomedical bundles, `statistical-modeling-bayes`, or `python-scripting` / `r-scripting`;
- omics / sequencing → the matching Biomedical bundle (single-cell, variant-calling, differential-expression, …);
- cohort / EHR queries → the **CDWAgent** or **UCSFOMOPAgent** extension.

### 5. Verification (the part that matters)
Before anything is written as fact, adversarially check it:
- Load `claim-evidence-integrity` and run its audit. It owns this stage: the claim ledger, the citation and temporal checks, and the runnable reference verifier against PubMed, CrossRef and OpenAlex.
- **Numbers:** re-derive every statistic from its source table or computation; never copy a number you cannot reproduce.
- **Claims:** for each load-bearing claim, ask "what would refute this?" and check whether the cited source actually supports it (not just that the source exists).
- Keep its ledger as the audit trail: claim → source → verified/unverified.

### 6. Write-up
Draft to the target format (review, abstract, methods, grant aim). For a manuscript or a manuscript section, load `scientific-manuscript-writing`, which owns drafting; `scientific-prose-review` line-edits the draft and `anti-ai-writing` strips AI tells. Use `grant-funding-strategy` for grant text and `scientific-artifacts` for slides, posters, diagrams and other deliverables. Cite inline against the verified source list only. Close with an explicit **limitations / unverified** section listing anything that could not be grounded.

---

## Division of labor

| Need | Use |
|---|---|
| Scholarly search and records | **LiteratureAgent**, **BioMCPAgent** extensions; `database-access`, `clinical-databases` bundles; **MedCP** if installed |
| Systematic review, meta-analysis | `systematic-review-prisma` |
| Knowledge-graph reasoning (gene/disease/drug) | **SPOKEAgent**, **PrimeKGAgent** extensions |
| Cohorts / EHR / OMOP queries | **CDWAgent**, **UCSFOMOPAgent** extensions |
| Empirical analysis stage | `empirical-research-router` |
| Scientific method gates | `science-superpowers` |
| Omics / sequencing analysis | matching Biomedical bundle |
| Stats / ML execution | `clinical-biostatistics`, `machine-learning` bundles, `statistical-modeling-bayes`, `python-scripting`, `r-scripting` |
| Claim, number and citation audit | `claim-evidence-integrity` |
| Figures | `ggplot-visualization`, `python-visualization`, the `data-visualization` bundle, `figure-qa` |
| Manuscript drafting and editing | `scientific-manuscript-writing`, `scientific-prose-review`, `anti-ai-writing` |
| Slides, posters, diagrams, reports | `scientific-artifacts` |
| Reproducibility and reporting checklists | `replication-package-audit` |
| Heavy compute | `ucsf-hpc` |
| Long autonomous build | `ralph` |
| Web UI for the result | `frontend-design` |

This skill is the conductor; those are the instruments. Reach for the most specific tool available and keep this skill focused on *deciding the path and verifying the output*.

---

## Anti-patterns

- Writing a "literature review" from memory instead of retrieval. **Don't.**
- Producing a polished draft with citations you never resolved. **Verify first.**
- Running all six stages on a question that only needed a scoped lookup. **Match effort to the task.**
- Hiding uncertainty to sound authoritative. **Name what you couldn't confirm.**
