# BioRouter Skills

A collection of **skills** for [BioRouter](https://github.com/BaranziniLab/BioRouter) — UCSF's local-first AI workspace for biomedical research.

Skills are reusable instruction bundles that BioRouter loads on demand to shape how the model writes code, drafts documents, reasons about a problem, and runs research. Some run automatically when relevant files are touched (style enforcement, language conventions, bioinformatics tasks). Others are *user-invocable* and respond to a slash command like `/ralph`, `/auto-research`, or `/anti-ai-writing` in the chat panel.

This repository hosts the skills curated by the [Baranzini Lab](https://baranzinilab.ucsf.edu/) at UCSF. Each top-level folder is a single skill; a few folders (`superpowers/`, `bio-skills/`) are bundled collections of many sub-skills.

---

## Installing a skill

1. Download the skill's `.zip` from the [Releases](https://github.com/BaranziniLab/biorouter-skills/releases) page.
2. Unzip it.
3. Move the resulting folder into `~/.config/biorouter/skills/`.
4. Open BioRouter. The skill appears under **Skills** automatically. User-invocable skills respond to `/skill-name`.

You can also drag a `.zip` (or a single `SKILL.md`) onto **Skills → Add Skill** inside BioRouter, or clone individual folders directly into `~/.config/biorouter/skills/` to track updates with `git`.

---

## Core skills

General-purpose skills — research, writing, planning, code style, and design.

| Skill | Trigger | What it does |
|---|---|---|
| [`scientific-research`](scientific-research) | `/scientific-research` | End-to-end research pipeline: scope → literature review → hypotheses → analysis plan → verification → cited write-up. Orchestrates `bio-skills` and the BioRouter extensions; never fabricates citations or results. |
| [`empirical-research-router`](empirical-research-router) | `/empirical-research-router` | Stage-gated empirical research workflow: design register, data audit, identification, estimation, robustness, replication, and reporting. |
| [`causal-identification-gates`](causal-identification-gates) | `/causal-identification-gates` | Audits whether RCT, observational, IV, RDD, DiD, synthetic-control, matching, DML, or survival designs support causal language. |
| [`replication-package-audit`](replication-package-audit) | `/replication-package-audit` | Checks research packages for clean-run reproducibility, relative paths, environment capture, seeds, logs, and table/figure mapping. |
| [`claim-evidence-integrity`](claim-evidence-integrity) | `/claim-evidence-integrity` | Verifies that manuscript claims, numbers, citations, figures, and tables are grounded in traceable evidence. |
| [`citation-temporal-integrity`](citation-temporal-integrity) | `/citation-temporal-integrity` | Confirms citations are real, relevant, current enough for the claim, and temporally valid. |
| [`empirical-benchmark-harness`](empirical-benchmark-harness) | `/empirical-benchmark-harness` | Provides known-answer benchmark patterns for testing whether empirical-analysis agents avoid common causal and reproducibility failures. |
| [`scientific-artifacts`](scientific-artifacts) | `/scientific-artifacts` | Plans and verifies DOCX/PDF/PPTX/XLSX/LaTeX/scientific figure artifacts with source-to-exhibit mapping. |
| [`open-science-review`](open-science-review) | `/open-science-review` | Reviews data/code availability, reporting checklists, protocols, ethics/privacy notes, and open-science readiness. |
| [`scientific-data-engineering`](scientific-data-engineering) | `/scientific-data-engineering` | Plans scalable scientific data workflows with Polars, Dask, Zarr, TileDB, Arrow/Parquet, HDF5, and dataset versioning. |
| [`statistical-modeling-bayes`](statistical-modeling-bayes) | `/statistical-modeling-bayes` | Designs and critiques statistical, Bayesian, survival, hierarchical, power, and uncertainty-reporting workflows. |
| [`scientific-machine-learning`](scientific-machine-learning) | `/scientific-machine-learning` | Plans scientific ML with leakage checks, transformers, graph neural networks, active learning, SHAP, and reproducibility gates. |
| [`geospatial-science`](geospatial-science) | `/geospatial-science` | Handles geospatial analysis with CRS checks, spatial joins, rasters/vectors, maps, and spatial statistics. |
| [`neurophysiology-analysis`](neurophysiology-analysis) | `/neurophysiology-analysis` | Plans biosignal and neural-recording analysis: ECG/EDA/PPG, spike sorting, Neuropixels metadata, and peri-event QC. |
| [`quantum-scientific-computing`](quantum-scientific-computing) | `/quantum-scientific-computing` | Routes quantum and scientific simulation work across Qiskit, Cirq, PennyLane, QuTiP, and validation checks. |
| [`materials-informatics`](materials-informatics) | `/materials-informatics` | Guides computational materials workflows with structures, crystals, compositions, phase diagrams, and dataset provenance. |
| [`biomedical-imaging-pathology`](biomedical-imaging-pathology) | `/biomedical-imaging-pathology` | Plans DICOM/pathology/PACS workflows with tiling, metadata, QC, cohort provenance, and privacy-safe reporting. |
| [`citation-library-management`](citation-library-management) | `/citation-library-management` | Builds, cleans, verifies, and deduplicates Zotero/BibTeX/RIS/CSL citation libraries. |
| [`laboratory-automation-planning`](laboratory-automation-planning) | `/laboratory-automation-planning` | Plans Opentrons/cloud-lab workflows with plate maps, protocol simulation, sample metadata, and execution gates. |
| [`econometrics-toolkit`](econometrics-toolkit) | `/econometrics-toolkit` | Plans applied econometrics in Python, R, or Stata: panel data, IV, DiD, RDD, clustering, and replication tables. |
| [`systematic-review-prisma`](systematic-review-prisma) | `/systematic-review-prisma` | Runs systematic-review workflows: PICO, search strings, screening logs, PRISMA flow, extraction, risk of bias, and synthesis. |
| [`simulation-optimization`](simulation-optimization) | `/simulation-optimization` | Plans discrete-event simulation, multi-objective optimization, sensitivity analysis, scheduling, and what-if modeling. |
| [`physical-science-computing`](physical-science-computing) | `/physical-science-computing` | Routes astronomy, physics, units, coordinate systems, spectra, numerical experiments, and physical-science workflows. |
| [`metabolic-modeling-cobrapy`](metabolic-modeling-cobrapy) | `/metabolic-modeling-cobrapy` | Guides COBRApy/FBA metabolic modeling with GPR rules, media constraints, knockouts, objectives, and provenance. |
| [`drug-discovery-benchmarks`](drug-discovery-benchmarks) | `/drug-discovery-benchmarks` | Plans ADMET, virtual-screening, molecular-property, scaffold-split, leakage, and assay-provenance benchmark checks. |
| [`clinical-decision-support-review`](clinical-decision-support-review) | `/clinical-decision-support-review` | Reviews clinical decision support, treatment plans, and reports for evidence grounding, safety scope, and no-PHI handling. |
| [`scientific-visual-communication`](scientific-visual-communication) | `/scientific-visual-communication` | Plans schematics, posters, slides, figure panels, infographics, visual abstracts, and source-to-visual traceability. |
| [`grant-funding-strategy`](grant-funding-strategy) | `/grant-funding-strategy` | Structures research grants, specific aims, milestones, reviewer-risk responses, and funder-fit checks. |
| [`regulatory-quality-systems`](regulatory-quality-systems) | `/regulatory-quality-systems` | Reviews scientific software, device, and lab processes against quality, validation, traceability, and design-control gates. |
| [`gpu-compute-optimization`](gpu-compute-optimization) | `/gpu-compute-optimization` | Plans GPU-bound training/inference, batching, profiling, memory pressure, mixed precision, and reproducible compute. |
| [`research-evaluation-venues`](research-evaluation-venues) | `/research-evaluation-venues` | Evaluates papers, scholars, venues, impact claims, reviewer fit, and publication positioning. |
| [`qualitative-thematic-analysis`](qualitative-thematic-analysis) | `/qualitative-thematic-analysis` | Plans qualitative coding, thematic analysis, codebooks, memoing, inter-rater checks, and audit trails. |
| [`financial-accounting-econometrics`](financial-accounting-econometrics) | `/financial-accounting-econometrics` | Plans empirical finance/accounting workflows with event studies, abnormal returns, panel data, and table replication. |
| [`anti-ai-writing`](anti-ai-writing) | `/anti-ai-writing` | Pass/fail checklist that strips AI tells out of prose, articles, and essays. |
| [`taste-skill`](taste-skill) | Auto (frontend design) | Anti-slop frontend design — landing pages, portfolios, dashboards, and paper companion sites that don't look templated. |
| [`develop-biorouter-extension`](develop-biorouter-extension) | `/develop-biorouter-extension` | Step-by-step guide for building a `.brxt` extension — manifest, MCP server, bundled skills. |
| [`ralph`](ralph) | `/ralph` | End-to-end planning for the **Ralph** autonomous agent loop — generates a markdown PRD from a feature idea, then converts it to `prd.json` sized for one-story-per-iteration execution. Adapted from [snarktank/ralph](https://github.com/snarktank/ralph) (MIT), itself based on [Geoffrey Huntley's Ralph pattern](https://ghuntley.com/ralph). |
| [`ucsf-hpc`](ucsf-hpc) | `/ucsf-hpc` | SSH setup, SLURM templates (CPU/GPU/H200), file transfer, and module management for the UCSF CHPC cluster. |
| [`python-scripting`](python-scripting) | Auto (Python) | Enforces Python naming, typing, error handling, and project-structure conventions. |
| [`r-scripting`](r-scripting) | Auto (R) | Tidyverse conventions and documentation standards for R. |
| [`ggplot-visualization`](ggplot-visualization) | Auto (R plotting) | Applies the lab's ggplot2 style whenever R plotting code is written. |
| [`superpowers`](superpowers) | Mixed | A bundled collection of 13 engineering-discipline skills (brainstorming, TDD, systematic debugging, parallel agents, plan writing, code review, git worktrees, more). |

---

## Developer & authoring skills

Engineering, review, and skill-authoring tools — adapted from [Anthropic's official Claude Code plugins](https://github.com/anthropics/claude-plugins-official) (Apache 2.0). Each upstream plugin ships as slash-commands and subagents (none of them carry lifecycle hooks); BioRouter has no `commands/` or `agents/` loader, so each plugin's commands and subagents are folded into one self-contained `SKILL.md` the model loads on demand. `hookify` is the exception — BioRouter has a hook engine, so it writes genuine, enforced hooks in `<project>/.biorouter/hooks.yaml` instead of honor-system notes.

| Skill | Trigger | What it does |
|---|---|---|
| [`code-review`](code-review) | `/code-review` | Multi-stage, confidence-scored review of a pull request (or local diff); drops low-confidence findings and posts a formatted PR comment via `gh`. |
| [`code-simplifier`](code-simplifier) | `/code-simplifier` | Simplifies recently-changed code for clarity while preserving exact behavior; defers language style to `python-scripting`/`r-scripting`. |
| [`commit-commands`](commit-commands) | `/commit-commands` | Three git workflows — clean single commit; commit + push + open PR; and clean up `[gone]` branches and their worktrees. |
| [`skill-creator`](skill-creator) | `/skill-creator` | The canonical guide to authoring BioRouter skills — frontmatter, progressive disclosure, packaging, and testing. |
| [`hookify`](hookify) | `/hookify` | Captures project guardrails (warn/block rules) and writes them as real Biorouter hooks in `<project>/.biorouter/hooks.yaml` — a `block` rule stops the action, a `warn` rule surfaces a notice. Requires `hooks.allow_project_hooks: true`. |
| [`code-modernization`](code-modernization) | `/code-modernization` | Phased legacy-modernization workflow: preflight → assess → map → extract rules → brief → transform → harden → status. |
| [`playground`](playground) | `/playground` | Generates self-contained single-file interactive HTML playgrounds for configuring something visually and copying out a prompt. |
| [`frontend-design`](frontend-design) | Auto (frontend work) | Anthropic's anti-slop frontend guidance; complements the `taste-skill`. |

---

## BioSkills — bioinformatics bundle

[`bio-skills/`](bio-skills) is a large, context-triggered bundle covering the working biologist's toolkit: sequence I/O, alignment, variant calling, single-cell, ATAC/ChIP-seq, proteomics, metabolomics, pathway analysis, machine learning, workflow management, and more — 466 individual skills across 63 categories in this snapshot. These load automatically when BioRouter sees a relevant file or task (a `.vcf`, a `scanpy` import, a `Seurat` object). See [`bio-skills/INDEX.md`](bio-skills/INDEX.md) for the full catalog.

Integrated from [GPTomics/bioSkills](https://github.com/GPTomics/bioSkills) (MIT-origin upstream) and distributed here as part of the Apache-2.0 BioRouter skills package with provenance preserved in the attribution table. BioRouter's house style prefers [`uv`](https://github.com/astral-sh/uv) over `pip`; skills with `pip install` lines carry a one-line uv tip banner while leaving the original commands intact for reproducibility.

`scientific-research` is designed to delegate to this bundle — and to the SPOKE, CDW, OMOP, and MedCP extensions — for any biomedical data access, so the orchestrator never has to recall facts from memory.

---

## Repository layout

```
biorouter-skills/
├── LICENSE                        ← Apache-2.0
├── NOTICE                         ← upstream attribution notes
├── auto-research/SKILL.md
├── anti-ai-writing/SKILL.md
├── taste-skill/SKILL.md
├── develop-biorouter-extension/SKILL.md
├── ggplot-visualization/SKILL.md
├── python-scripting/SKILL.md
├── r-scripting/SKILL.md
├── ucsf-hpc/SKILL.md
├── ralph/
│   ├── SKILL.md                   ← the skill itself
│   ├── agent-instructions.md      ← prompt for the autonomous loop
│   └── prd.json.example
├── superpowers/                   ← 13 sub-skill collection
│   ├── brainstorming/
│   ├── test-driven-development/
│   └── …
└── bio-skills/                    ← bioinformatics bundle (63 categories)
    ├── INDEX.md
    ├── single-cell/
    ├── variant-calling/
    └── …
```

Every skill folder contains a `SKILL.md` with YAML frontmatter (`name`, `description`, optional `user-invocable`). Anything else in the folder is supporting material the skill can reference.

---

## Contributing a new skill

1. Fork this repo.
2. Add a new top-level folder named after your skill (kebab-case).
3. Drop a `SKILL.md` into it with frontmatter:

   ```markdown
   ---
   name: my-skill
   description: One sentence — what it does and when to use it. This is the line the model reads to decide whether to load the skill.
   license: Apache-2.0
   user-invocable: true   # optional
   ---

   # My Skill

   The skill body. Be concrete, give examples, and keep it focused on one job.
   ```

4. Open a pull request. A maintainer will review and cut a release with a matching `.zip` so BAAM picks it up automatically.

A good `description:` is the single most important line — it is what the model sees when deciding whether to invoke the skill, so be specific about *when* to use it, not just *what* it does.

---

## Sources & attribution

This repository is licensed under the [Apache License 2.0](LICENSE). Every distributed `SKILL.md` declares `license: Apache-2.0` so BioRouter and BAAM can surface the license consistently. Several skills are adapted from permissively licensed open-source projects; we preserve those upstream credits and original license families in the table below. Lab-original skills are written by the [Baranzini Lab](https://baranzinilab.ucsf.edu/).

| Skill | Source | License | What changed for BioRouter |
|---|---|---|---|
| `bio-skills` | [GPTomics/bioSkills](https://github.com/GPTomics/bioSkills), plus BioRouter-original Apache-2.0 additions inspired by Scientific Agent Skills | Distributed as Apache-2.0 in BioRouter; GPTomics origin was MIT | Dropped the `bio-` name prefix, set `user-invocable: false`, and added a one-line `uv` tip banner to skills that shipped `pip install` commands (originals left intact). 466 skills / 63 categories in this snapshot, including new PyDESeq2, compound hygiene, DeepChem, protein language model, DiffDock, Nextflow/nf-core, causal ML, SHAP, Python visualization, and literature-discovery skills. |
| `taste-skill` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) | Distributed as Apache-2.0 in BioRouter; upstream origin was MIT | Wired to BioRouter's auto-trigger on frontend work; content kept. Attribution header retained in the `SKILL.md`. |
| `superpowers` | [obra/superpowers](https://github.com/obra/superpowers) by Jesse Vincent | Distributed as Apache-2.0 in BioRouter; upstream origin was MIT | Folded the 13 engineering-discipline skills in; dropped the upstream `using-superpowers` dispatcher and its `SessionStart` hook (BioRouter discovers skills natively). `verification-before-completion` and `finishing-a-development-branch` gained an optional `Stop`-hook recipe to hard-enforce "tests pass before finishing." |
| `ralph` | [snarktank/ralph](https://github.com/snarktank/ralph) by Ryan Carson, after [Geoffrey Huntley's Ralph pattern](https://ghuntley.com/ralph) | Distributed as Apache-2.0 in BioRouter; upstream origin was MIT | Reworked the PRD → `prd.json` → one-story-per-iteration flow around BioRouter's agent loop and `/ralph` invocation. |
| `code-review`, `code-simplifier`, `commit-commands`, `skill-creator`, `code-modernization`, `playground`, `frontend-design` | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) | Apache-2.0 | Each upstream plugin's slash-commands and subagents folded into one `SKILL.md` (these plugins ship no hooks). Shell routed through the Developer extension; lab-specific defaults adjusted. Each `SKILL.md` keeps a source header. |
| `hookify` | [anthropics/claude-plugins-official → hookify](https://github.com/anthropics/claude-plugins-official/tree/main/plugins/hookify) | Apache-2.0 | Rewritten to generate real, enforced BioRouter hooks (`<project>/.biorouter/hooks.yaml`) — the upstream's enforced-hook behavior, expressed in BioRouter's native hook schema. |
| `scientific-research` | Lab-original | Apache-2.0 | — Orchestrates `bio-skills` and the SPOKE / CDW / OMOP / MedCP extensions. |
| `empirical-research-router`, `causal-identification-gates`, `replication-package-audit`, `claim-evidence-integrity`, `citation-temporal-integrity`, `empirical-benchmark-harness`, `scientific-artifacts`, `open-science-review` | Lab-original synthesis inspired by [k-dense-ai/scientific-agent-skills](https://github.com/k-dense-ai/scientific-agent-skills) and [brycewang-stanford/Auto-Empirical-Research-Skills](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills) | Apache-2.0 | Rewritten as native BioRouter skills with stage gates, citation/claim audits, and reproducibility checks. No upstream text copied. |
| `scientific-data-engineering`, `statistical-modeling-bayes`, `scientific-machine-learning`, `geospatial-science`, `neurophysiology-analysis`, `quantum-scientific-computing`, `materials-informatics`, `biomedical-imaging-pathology`, `citation-library-management`, `laboratory-automation-planning`, `econometrics-toolkit`, `systematic-review-prisma` | Lab-original capability-cluster synthesis inspired by [k-dense-ai/scientific-agent-skills](https://github.com/k-dense-ai/scientific-agent-skills) and [brycewang-stanford/Auto-Empirical-Research-Skills](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills) | Apache-2.0 | Rewritten as native BioRouter routing and quality-gate skills for remaining tool/library families. No upstream text copied. |
| `simulation-optimization`, `physical-science-computing`, `metabolic-modeling-cobrapy`, `drug-discovery-benchmarks`, `clinical-decision-support-review`, `scientific-visual-communication`, `grant-funding-strategy`, `regulatory-quality-systems`, `gpu-compute-optimization`, `research-evaluation-venues`, `qualitative-thematic-analysis`, `financial-accounting-econometrics` | Lab-original capability-cluster synthesis inspired by [k-dense-ai/scientific-agent-skills](https://github.com/k-dense-ai/scientific-agent-skills) and [brycewang-stanford/Auto-Empirical-Research-Skills](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills) | Apache-2.0 | Rewritten as native BioRouter routing and verification skills for simulation, physical science, regulatory, visual, grant, and empirical discipline clusters. No upstream text copied. |
| `anti-ai-writing` | Lab-original | Apache-2.0 | — Prose checklist for stripping AI tells. |
| `ucsf-hpc` | Lab-original | Apache-2.0 | — UCSF CHPC cluster: SSH, SLURM templates, modules. |
| `python-scripting`, `r-scripting`, `ggplot-visualization` | Lab-original | Apache-2.0 | — House style for Python, R, and ggplot2; auto-triggered by file context. |
| `develop-biorouter-extension` | Lab-original | Apache-2.0 | — Guide for the `.brxt` extension format. |

Maintained by the [Baranzini Lab](https://baranzinilab.ucsf.edu/) at UCSF.
