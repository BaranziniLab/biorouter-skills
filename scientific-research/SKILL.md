---
name: scientific-research
description: Run a research question end to end — scoping, literature review, hypothesis generation, analysis planning, result verification, and a cited write-up. Use when the user wants to investigate a topic, survey prior work, plan or critique an analysis, draft a paper section, or run a multi-step "do the research for me" task. Delegates biomedical data access to the bio-skills bundle and to BioRouter extensions (SPOKE, CDW, OMOP, MedCP).
user-invocable: true
---

# Scientific Research

A pipeline for taking a research question from a one-line prompt to a verified, cited draft — without inventing facts. This skill is the **orchestrator**: it decides the path, then hands the domain work to the right tool. It does not replace a scientist's judgment; every claim it surfaces is meant to be checked, and it flags where it is uncertain.

> **House rule: no fabrication.** Never invent a citation, a DOI, a statistic, or a result. If a fact cannot be grounded in a retrieved source or a real computation, say so explicitly. A hallucinated reference is worse than a missing one.

---

## When this fires

Use `/scientific-research` (or let it auto-load) when the request is a *research task*, not a code task:

- "What's known about X?" / "Survey the literature on Y."
- "Generate hypotheses for why Z happens."
- "Plan an analysis to test this." / "Is this analysis sound?"
- "Draft the introduction / methods / discussion for this."
- "Do the background research and write it up."

If the request is purely "write this code" or "run this tool," defer to `python-scripting`, `r-scripting`, the `bio-skills` bundle, or the relevant extension instead.

---

## The loop

Run only the stages the task needs. Most requests need 2–4 of these, not all six.

### 1. Scope
Restate the question in one sentence. Name the deliverable (a survey? a hypothesis list? a methods paragraph?), the audience, and the stop condition. List what you already know vs. what you must retrieve. Surface ambiguities to the user *before* spending effort — a wrong scope wastes every later stage.

### 2. Literature review
Retrieve real sources; never recall them from memory.
- **Biomedical / clinical:** route through the `bio-skills` **database-access** and **clinical-databases** skills (PubMed, PMC, bioRxiv/medRxiv, ClinicalTrials.gov, OpenAlex, Crossref) and, if installed, the **MedCP** extension. For knowledge-graph context (gene–disease–drug relationships) use the **SPOKEAgent** extension.
- **General:** use whatever web-search / paper-API tool BioRouter exposes.
- For every source, capture: title, authors, year, venue, and a stable ID (DOI / PMID / arXiv). Drop anything you cannot resolve to a real identifier.
- Summarize per-source, then synthesize across sources. Note agreements, contradictions, and gaps — the gaps often *are* the contribution.

### 3. Hypothesis generation
From the synthesis, propose testable hypotheses. For each: state the mechanism, the prediction, and what evidence would confirm or refute it. Rank by novelty × testability. Mark which are already settled in the literature (don't re-propose known results).

### 4. Analysis planning
Translate a hypothesis into a concrete plan: data source, variables, model, assumptions, sample-size / power reasoning, confounders, and the pre-registered decision rule (what result means what *before* you look). For execution, hand off:
- statistics & ML → `bio-skills` **clinical-biostatistics** / **machine-learning**, or `python-scripting` / `r-scripting`;
- omics / sequencing → the matching `bio-skills` category (single-cell, variant-calling, differential-expression, …);
- cohort / EHR queries → the **CDWAgent** or **UCSFOMOPAgent** extension.

### 5. Verification (the part that matters)
Before anything is written as fact, adversarially check it:
- **Citations:** confirm every reference resolves to a real record (Crossref / PubMed lookup) and that the title/authors/year match — catch hallucinated bibliographies.
- **Numbers:** re-derive every statistic from its source table or computation; never copy a number you cannot reproduce.
- **Claims:** for each load-bearing claim, ask "what would refute this?" and check whether the cited source actually supports it (not just that the source exists).
- Record a short audit trail: claim → source → verified/unverified.

### 6. Write-up
Draft to the target format (review, abstract, methods, grant aim). Cite inline against the verified source list only. Keep the voice plain — pair with the `anti-ai-writing` skill to strip AI tells, and with `taste-skill` if the deliverable is a web page or dashboard. Close with an explicit **limitations / unverified** section listing anything that could not be grounded.

---

## Division of labor

| Need | Use |
|---|---|
| Biomedical literature & databases | `bio-skills` (database-access, clinical-databases), **MedCP** extension |
| Knowledge-graph reasoning (gene/disease/drug) | **SPOKEAgent** extension |
| Cohorts / EHR / OMOP queries | **CDWAgent**, **UCSFOMOPAgent** extensions |
| Omics / sequencing analysis | matching `bio-skills` category |
| Stats / ML execution | `bio-skills` (clinical-biostatistics, machine-learning), `python-scripting`, `r-scripting` |
| Figures | `ggplot-visualization`, `bio-skills` data-visualization |
| Heavy compute | `ucsf-hpc` |
| Long autonomous build | `ralph` |
| De-AI the prose | `anti-ai-writing` |
| Web UI for the result | `taste-skill` |

This skill is the conductor; those are the instruments. Reach for the most specific tool available and keep this skill focused on *deciding the path and verifying the output*.

---

## Anti-patterns

- Writing a "literature review" from memory instead of retrieval. **Don't.**
- Producing a polished draft with citations you never resolved. **Verify first.**
- Running all six stages on a question that only needed a scoped lookup. **Match effort to the task.**
- Hiding uncertainty to sound authoritative. **Name what you couldn't confirm.**
