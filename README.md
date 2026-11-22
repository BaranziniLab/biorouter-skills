# Biorouter Skills

The **skills** of [BAAM](https://biorouter.ucsf.edu/baam.html), the marketplace of [Biorouter](https://github.com/BaranziniLab/biorouter), UCSF's local-first AI workspace for biomedical research.

Skills are instruction bundles that Biorouter loads on demand to shape how the model writes code, drafts documents, reasons about a problem and runs research. Some load automatically when a task matches their description; others are *user-invocable* and answer a slash command such as `/scientific-research` in the chat.

This repository is curated by the [Baranzini Lab](https://baranzinilab.ucsf.edu/) at UCSF. Each top-level folder is one skill or a bundle of skills, `bio-skills/<id>/` holds the biomedical bundles, and [`catalog.json`](catalog.json) records every item, active or not.

<!-- catalog:begin counts -->
57 core skills, 9 developer skills and 63 biomedical bundles (466 skills) are active; 0 older skills have moved or retired.
<!-- catalog:end counts -->

---

## Installing a skill

In Biorouter, open **Skills**, choose **Browse**, and add the skill from BAAM. To install a downloaded archive instead, use **Skills → Add Skill** and pick the `.zip` from the [Releases](https://github.com/BaranziniLab/biorouter-skills/releases) page, or run `biorouter skill install <path-or-url>` in a terminal.

Each skill is released under the tag `skill-<id>` as `<id>.zip`. To update an installed skill, remove it and add it again; the agent's marketplace install replaces an installed copy.

---

## Core skills

<!-- catalog:begin core -->
| Skill | Version | Invocation | Licence | What it does |
|---|---|---|---|---|
| [`scientific-research`](scientific-research) | 1.0.0 | `/scientific-research` | Apache-2.0 | End-to-end research: scopes the question, reviews real literature, generates hypotheses, plans and verifies the analysis, then writes a cited draft. Delegates biomedical data queries to whichever data extensions are installed. It never fabricates a citation or result. |
| [`empirical-research-router`](empirical-research-router) | 1.0.0 | `/empirical-research-router` | Apache-2.0 | Stage-gated empirical research workflow: design register, data audit, identification, estimation, robustness, replication, and reporting. |
| [`causal-identification-gates`](causal-identification-gates) | 1.0.0 | `/causal-identification-gates` | Apache-2.0 | Audits whether RCT, observational, IV, RDD, DiD, synthetic-control, matching, DML, or survival designs support causal language. |
| [`replication-package-audit`](replication-package-audit) | 1.0.0 | `/replication-package-audit` | Apache-2.0 | Checks research packages for clean-run reproducibility, relative paths, environment capture, seeds, logs, and table/figure mapping. |
| [`claim-evidence-integrity`](claim-evidence-integrity) | 1.0.0 | `/claim-evidence-integrity` | Apache-2.0 | Verifies that manuscript claims, numbers, citations, figures, and tables are grounded in traceable evidence. |
| [`citation-temporal-integrity`](citation-temporal-integrity) | 1.0.0 | `/citation-temporal-integrity` | Apache-2.0 | Confirms citations are real, relevant, current enough for the claim, and temporally valid. |
| [`empirical-benchmark-harness`](empirical-benchmark-harness) | 1.0.0 | `/empirical-benchmark-harness` | Apache-2.0 | Known-answer benchmark patterns for testing whether empirical-analysis agents avoid common causal and reproducibility failures. |
| [`scientific-artifacts`](scientific-artifacts) | 1.0.0 | `/scientific-artifacts` | Apache-2.0 | Plans and verifies DOCX/PDF/PPTX/XLSX/LaTeX/scientific figure artifacts with source-to-exhibit mapping. |
| [`open-science-review`](open-science-review) | 1.0.0 | `/open-science-review` | Apache-2.0 | Reviews data/code availability, reporting checklists, protocols, ethics/privacy notes, and open-science readiness. |
| [`scientific-data-engineering`](scientific-data-engineering) | 1.0.0 | `/scientific-data-engineering` | Apache-2.0 | Plans scalable scientific data workflows with Polars, Dask, Zarr, TileDB, Arrow/Parquet, HDF5, and dataset versioning. |
| [`statistical-modeling-bayes`](statistical-modeling-bayes) | 1.0.0 | `/statistical-modeling-bayes` | Apache-2.0 | Designs and critiques statistical, Bayesian, survival, hierarchical, power, and uncertainty-reporting workflows. |
| [`scientific-machine-learning`](scientific-machine-learning) | 1.0.0 | `/scientific-machine-learning` | Apache-2.0 | Plans scientific ML with leakage checks, transformers, graph neural networks, active learning, SHAP, and reproducibility gates. |
| [`geospatial-science`](geospatial-science) | 1.0.0 | `/geospatial-science` | Apache-2.0 | Handles geospatial analysis with CRS checks, spatial joins, rasters/vectors, maps, and spatial statistics. |
| [`neurophysiology-analysis`](neurophysiology-analysis) | 1.0.0 | `/neurophysiology-analysis` | Apache-2.0 | Plans biosignal and neural-recording analysis: ECG/EDA/PPG, spike sorting, Neuropixels metadata, and peri-event QC. |
| [`quantum-scientific-computing`](quantum-scientific-computing) | 1.0.0 | `/quantum-scientific-computing` | Apache-2.0 | Routes quantum and scientific simulation work across Qiskit, Cirq, PennyLane, QuTiP, and validation checks. |
| [`materials-informatics`](materials-informatics) | 1.0.0 | `/materials-informatics` | Apache-2.0 | Guides computational materials workflows with structures, crystals, compositions, phase diagrams, and dataset provenance. |
| [`biomedical-imaging-pathology`](biomedical-imaging-pathology) | 1.0.0 | `/biomedical-imaging-pathology` | Apache-2.0 | Plans DICOM/pathology/PACS workflows with tiling, metadata, QC, cohort provenance, and privacy-safe reporting. |
| [`citation-library-management`](citation-library-management) | 1.0.0 | `/citation-library-management` | Apache-2.0 | Builds, cleans, verifies, and deduplicates Zotero/BibTeX/RIS/CSL citation libraries. |
| [`laboratory-automation-planning`](laboratory-automation-planning) | 1.0.0 | `/laboratory-automation-planning` | Apache-2.0 | Plans Opentrons/cloud-lab workflows with plate maps, protocol simulation, sample metadata, and execution gates. |
| [`econometrics-toolkit`](econometrics-toolkit) | 1.0.0 | `/econometrics-toolkit` | Apache-2.0 | Plans applied econometrics in Python, R, or Stata: panel data, IV, DiD, RDD, clustering, and replication tables. |
| [`systematic-review-prisma`](systematic-review-prisma) | 1.0.0 | `/systematic-review-prisma` | Apache-2.0 | Runs systematic-review workflows: PICO, search strings, screening logs, PRISMA flow, extraction, risk of bias, and synthesis. |
| [`taste-skill`](taste-skill) | 1.0.0 | Auto | Apache-2.0 | Anti-slop frontend design for landing pages, dashboards, lab tools, and paper companion sites. Reads the brief, picks a real design direction, and ships interfaces that don't look templated. |
| [`simulation-optimization`](simulation-optimization) | 1.0.0 | `/simulation-optimization` | Apache-2.0 | Plans discrete-event simulation, multi-objective optimization, sensitivity analysis, scheduling, and what-if modeling. |
| [`physical-science-computing`](physical-science-computing) | 1.0.0 | `/physical-science-computing` | Apache-2.0 | Routes astronomy, physics, units, coordinate systems, spectra, numerical experiments, and physical-science workflows. |
| [`metabolic-modeling-cobrapy`](metabolic-modeling-cobrapy) | 1.0.0 | `/metabolic-modeling-cobrapy` | Apache-2.0 | Guides COBRApy/FBA metabolic modeling with GPR rules, media constraints, knockouts, objectives, and provenance. |
| [`drug-discovery-benchmarks`](drug-discovery-benchmarks) | 1.0.0 | `/drug-discovery-benchmarks` | Apache-2.0 | Plans ADMET, virtual-screening, molecular-property, scaffold-split, leakage, and assay-provenance benchmark checks. |
| [`clinical-decision-support-review`](clinical-decision-support-review) | 1.0.0 | `/clinical-decision-support-review` | Apache-2.0 | Reviews clinical decision support, treatment plans, and reports for evidence grounding, safety scope, and no-PHI handling. |
| [`scientific-visual-communication`](scientific-visual-communication) | 1.0.0 | `/scientific-visual-communication` | Apache-2.0 | Plans schematics, posters, slides, figure panels, infographics, visual abstracts, and source-to-visual traceability. |
| [`grant-funding-strategy`](grant-funding-strategy) | 1.0.0 | `/grant-funding-strategy` | Apache-2.0 | Structures research grants, specific aims, milestones, reviewer-risk responses, and funder-fit checks. |
| [`regulatory-quality-systems`](regulatory-quality-systems) | 1.0.0 | `/regulatory-quality-systems` | Apache-2.0 | Reviews scientific software, device, and lab processes against quality, validation, traceability, and design-control gates. |
| [`gpu-compute-optimization`](gpu-compute-optimization) | 1.0.0 | `/gpu-compute-optimization` | Apache-2.0 | Plans GPU-bound training/inference, batching, profiling, memory pressure, mixed precision, and reproducible compute. |
| [`research-evaluation-venues`](research-evaluation-venues) | 1.0.0 | `/research-evaluation-venues` | Apache-2.0 | Evaluates papers, scholars, venues, impact claims, reviewer fit, and publication positioning. |
| [`qualitative-thematic-analysis`](qualitative-thematic-analysis) | 1.0.0 | `/qualitative-thematic-analysis` | Apache-2.0 | Plans qualitative coding, thematic analysis, codebooks, memoing, inter-rater checks, and audit trails. |
| [`financial-accounting-econometrics`](financial-accounting-econometrics) | 1.0.0 | `/financial-accounting-econometrics` | Apache-2.0 | Plans empirical finance/accounting workflows with event studies, abnormal returns, panel data, and table replication. |
| [`stata-research-workbench`](stata-research-workbench) | 1.0.0 | `/stata-research-workbench` | Apache-2.0 | Plans Stata .do/.dta research workflows: audits, logs, tables, graph export, replication, and R&R updates. |
| [`survey-weights-complex-samples`](survey-weights-complex-samples) | 1.0.0 | `/survey-weights-complex-samples` | Apache-2.0 | Handles complex survey designs with strata, PSUs, replicate weights, domain analysis, calibration, and weighted inference. |
| [`psychometrics-sem-measurement`](psychometrics-sem-measurement) | 1.0.0 | `/psychometrics-sem-measurement` | Apache-2.0 | Plans reliability, CFA/SEM, mediation/moderation, invariance, item analysis, and APA-style measurement reporting. |
| [`social-science-text-as-data`](social-science-text-as-data) | 1.0.0 | `/social-science-text-as-data` | Apache-2.0 | Plans dictionaries, topic models, embeddings, sentiment, supervised coding, LLM-label validation, and measurement-error checks. |
| [`econ-finance-data-sources`](econ-finance-data-sources) | 1.0.0 | `/econ-finance-data-sources` | Apache-2.0 | Routes empirical econ/finance sources including WRDS, CRSP, Compustat, SEC/EDGAR, NBER, SSRN, and public datasets. |
| [`empirical-paper-submission-rr`](empirical-paper-submission-rr) | 1.0.0 | `/empirical-paper-submission-rr` | Apache-2.0 | Plans journal targeting, referee reports, response letters, revise-and-resubmit execution, and appendix organization. |
| [`structural-economics-theory`](structural-economics-theory) | 1.0.0 | `/structural-economics-theory` | Apache-2.0 | Routes game theory, equilibrium, DSGE/HANK, structural IO, calibration, simulation, and identification-proof workflows. |
| [`causal-heterogeneity-policy-learning`](causal-heterogeneity-policy-learning) | 1.0.0 | `/causal-heterogeneity-policy-learning` | Apache-2.0 | Plans CATE, causal forests, meta-learners, policy learning, conformal causal inference, fairness, and subgroup reporting. |
| [`autoskill-workflow-discovery`](autoskill-workflow-discovery) | 1.0.0 | `/autoskill-workflow-discovery` | Apache-2.0 | Detects repeated workflows and drafts native Biorouter skills, hooks, checklist updates, or extension plans. |
| [`arbor-optimization`](arbor-optimization) | 1.0.0 | `/arbor-optimization` | Apache-2.0 | Runs evaluator-driven branch-and-prune exploration for improving research artifacts, prompts, analyses, and designs. |
| [`hugging-science-resource-discovery`](hugging-science-resource-discovery) | 1.0.0 | `/hugging-science-resource-discovery` | Apache-2.0 | Finds and evaluates Hugging Face scientific models, datasets, Spaces, and papers with license and provenance checks. |
| [`molecular-dynamics`](molecular-dynamics) | 1.0.0 | `/molecular-dynamics` | Apache-2.0 | Plans MD setup and trajectory analysis with OpenMM, GROMACS, AmberTools, MDAnalysis, MDTraj, and reproducibility checks. |
| [`general-time-series-forecasting`](general-time-series-forecasting) | 1.0.0 | `/general-time-series-forecasting` | Apache-2.0 | Plans non-omics forecasting with classical models, ML, foundation models, backtesting, leakage checks, and uncertainty. |
| [`bids-neuroimaging`](bids-neuroimaging) | 1.0.0 | `/bids-neuroimaging` | Apache-2.0 | Audits BIDS neuroimaging datasets, derivatives, validation, metadata, and reproducible preprocessing readiness. |
| [`clinical-ai-modeling`](clinical-ai-modeling) | 1.0.0 | `/clinical-ai-modeling` | Apache-2.0 | Plans clinical AI modeling workflows with EHR cohorts, validation, bias checks, calibration, safety, and no-PHI handling. |
| [`computational-fluid-dynamics`](computational-fluid-dynamics) | 1.0.0 | `/computational-fluid-dynamics` | Apache-2.0 | Plans CFD workflows with meshes, boundary conditions, turbulence models, solver validation, and convergence checks. |
| [`anti-ai-writing`](anti-ai-writing) | 1.0.0 | `/anti-ai-writing` | Apache-2.0 | A pass/fail checklist for spotting AI writing patterns before generating prose, articles, or essays. |
| [`ggplot-visualization`](ggplot-visualization) | 1.0.0 | Auto | Apache-2.0 | Applies ggplot2 best-practice style when writing R plotting code. |
| [`r-scripting`](r-scripting) | 1.0.0 | Auto | Apache-2.0 | Applies tidyverse conventions and documentation standards when writing or reviewing R code. |
| [`python-scripting`](python-scripting) | 1.0.0 | Auto | Apache-2.0 | Applies Python naming, typing, error handling, and project structure conventions when writing Python code. |
| [`ralph`](ralph) | 1.0.0 | `/ralph` | Apache-2.0 | End-to-end planning for the Ralph autonomous agent loop. Drafts a markdown PRD from a feature idea, then converts it to prd.json. Each story is sized for one hands-off iteration. |
| [`superpowers`](superpowers) | 1.0.0 | Bundle, 13 skills | Apache-2.0 | Engineering discipline skills: brainstorming, TDD, systematic debugging, parallel agents, plan writing, code review, git worktrees. Workflows tested on long-running engineering tasks. |
| [`ucsf-hpc`](ucsf-hpc) | 1.0.0 | `/ucsf-hpc` | Apache-2.0 | SSH setup, SLURM job templates (CPU/GPU/H200), file transfer, module management, and common pitfalls for the UCSF CHPC cluster. |
<!-- catalog:end core -->

---

## Developer and authoring skills

Several of these are adapted from [Anthropic's official Claude Code plugins](https://github.com/anthropics/claude-plugins-official) (Apache-2.0). Biorouter has no loader for plugin commands or subagents, so each plugin is folded into one self-contained `SKILL.md`. `hookify` writes real, enforced hooks in `<project>/.biorouter/hooks.yaml`.

<!-- catalog:begin developer -->
| Skill | Version | Invocation | Licence | What it does |
|---|---|---|---|---|
| [`code-review`](code-review) | 1.0.0 | `/code-review` | Apache-2.0 | Multi-stage, confidence-scored review of a pull request or local diff. Drops low-confidence findings and posts a formatted PR comment via gh. |
| [`code-simplifier`](code-simplifier) | 1.0.0 | `/code-simplifier` | Apache-2.0 | Simplifies recently-changed code for clarity and consistency while preserving exact behavior. Defers language style to the Python and R skills. |
| [`commit-commands`](commit-commands) | 1.0.0 | `/commit-commands` | Apache-2.0 | Three git workflows: a clean single commit; commit + push + open a PR; and cleanup of [gone] branches and their worktrees. |
| [`skill-creator`](skill-creator) | 1.0.0 | `/skill-creator` | Apache-2.0 | The canonical guide to authoring Biorouter skills: frontmatter, progressive disclosure, packaging, and testing. |
| [`develop-biorouter-extension`](develop-biorouter-extension) | 1.0.0 | `/develop-biorouter-extension` | Apache-2.0 | Step-by-step guide for building a .brxt extension: manifest, MCP server, packaging, validation, and bundled skills. |
| [`hookify`](hookify) | 1.0.0 | `/hookify` | Apache-2.0 | Turns project guardrails (warn/block rules) into real Biorouter hooks in .biorouter/hooks.yaml. A block rule stops the action; a warn rule shows a notice. Requires allow_project_hooks: true. |
| [`code-modernization`](code-modernization) | 1.0.0 | `/code-modernization` | Apache-2.0 | Phased legacy-modernization workflow (preflight, assess, map, extract rules, brief, transform, harden, status) for COBOL, legacy Java/C++, and monoliths. |
| [`playground`](playground) | 1.0.0 | `/playground` | Apache-2.0 | Generates self-contained single-file interactive HTML playgrounds for configuring something visually, then copying out a ready-to-use prompt. |
| [`frontend-design`](frontend-design) | 1.0.0 | Auto | Apache-2.0 | Anthropic's anti-slop frontend guidance for distinctive, production-grade UIs. Complements the Taste skill above. |
<!-- catalog:end developer -->

---

## Biomedical bundles

[`bio-skills/`](bio-skills) holds bundles that load automatically when Biorouter sees a relevant file or task (a `.vcf`, a `scanpy` import, a Seurat object). They come from [GPTomics/bioSkills](https://github.com/GPTomics/bioSkills) (MIT) plus Biorouter-original additions. Biorouter prefers [`uv`](https://github.com/astral-sh/uv) over `pip`; skills with `pip install` lines carry a one-line uv tip and keep the original commands. See [`bio-skills/INDEX.md`](bio-skills/INDEX.md) for every skill.

<!-- catalog:begin biomedical -->
| Bundle | Version | Skills | What it covers |
|---|---|---|---|
| [`alignment`](bio-skills/alignment) | 1.0.0 | 7 | Multiple sequence alignment and pairwise alignment. |
| [`alignment-files`](bio-skills/alignment-files) | 1.0.0 | 10 | SAM/BAM/CRAM manipulation, sorting, indexing, dedup, and stats. |
| [`alternative-splicing`](bio-skills/alternative-splicing) | 1.0.0 | 9 | RNA isoform and splice-junction analysis from short- and long-read data. |
| [`atac-seq`](bio-skills/atac-seq) | 1.0.0 | 12 | Chromatin accessibility, peak calling, footprinting, and deep-learning ATAC. |
| [`causal-genomics`](bio-skills/causal-genomics) | 1.0.0 | 11 | Mendelian randomization, colocalization, fine-mapping, and TWAS. |
| [`chemoinformatics`](bio-skills/chemoinformatics) | 1.0.0 | 9 | Molecular structure handling, descriptors, and drug-discovery utilities. |
| [`chip-seq`](bio-skills/chip-seq) | 1.0.0 | 7 | Transcription-factor and histone-mark peak calling and differential binding. |
| [`clinical-biostatistics`](bio-skills/clinical-biostatistics) | 1.0.0 | 6 | Survival, mixed models, and clinical-trial statistical analysis. |
| [`clinical-databases`](bio-skills/clinical-databases) | 1.0.0 | 10 | ClinVar, OMIM, COSMIC, gnomAD, and phenotype DB queries. |
| [`clip-seq`](bio-skills/clip-seq) | 1.0.0 | 5 | Protein-RNA interaction mapping from iCLIP/eCLIP/PAR-CLIP data. |
| [`comparative-genomics`](bio-skills/comparative-genomics) | 1.0.0 | 5 | Cross-species synteny, orthology, and selection scans. |
| [`copy-number`](bio-skills/copy-number) | 1.0.0 | 4 | CNV detection, visualization, and segmentation. |
| [`crispr-screens`](bio-skills/crispr-screens) | 1.0.0 | 8 | Pooled screen counting, MAGeCK analysis, and hit prioritization. |
| [`data-visualization`](bio-skills/data-visualization) | 1.0.0 | 13 | Publication-quality plots: heatmaps, volcano, Manhattan, dimplots. |
| [`database-access`](bio-skills/database-access) | 1.0.0 | 12 | NCBI, UniProt, Ensembl, and biological database APIs. |
| [`differential-expression`](bio-skills/differential-expression) | 1.0.0 | 7 | RNA-seq DE testing with DESeq2, edgeR, and limma-voom. |
| [`ecological-genomics`](bio-skills/ecological-genomics) | 1.0.0 | 6 | Environmental DNA, ecological population genomics, and biodiversity. |
| [`epidemiological-genomics`](bio-skills/epidemiological-genomics) | 1.0.0 | 5 | Pathogen typing, outbreak phylogeography, and surveillance. |
| [`epitranscriptomics`](bio-skills/epitranscriptomics) | 1.0.0 | 5 | m6A and other RNA modification detection from sequencing. |
| [`experimental-design`](bio-skills/experimental-design) | 1.0.0 | 4 | Power analysis and sample-size calculation for omics studies. |
| [`expression-matrix`](bio-skills/expression-matrix) | 1.0.0 | 5 | Count normalization, gene ID mapping, and matrix QC. |
| [`flow-cytometry`](bio-skills/flow-cytometry) | 1.0.0 | 8 | FCS parsing, gating, and high-dimensional cytometry analysis. |
| [`gene-regulatory-networks`](bio-skills/gene-regulatory-networks) | 1.0.0 | 5 | TF-target network inference from expression and chromatin data. |
| [`genome-annotation`](bio-skills/genome-annotation) | 1.0.0 | 6 | Gene prediction, repeat masking, and functional annotation. |
| [`genome-assembly`](bio-skills/genome-assembly) | 1.0.0 | 8 | De novo assembly, polishing, and assembly QC. |
| [`genome-engineering`](bio-skills/genome-engineering) | 1.0.0 | 5 | CRISPR guide design, off-target prediction, and editing analysis. |
| [`genome-intervals`](bio-skills/genome-intervals) | 1.0.0 | 7 | BED/GTF arithmetic, overlap, and feature manipulation. |
| [`hi-c-analysis`](bio-skills/hi-c-analysis) | 1.0.0 | 8 | 3D chromatin contacts, TAD calling, and loop detection. |
| [`imaging-mass-cytometry`](bio-skills/imaging-mass-cytometry) | 1.0.0 | 6 | Single-cell spatial proteomics from IMC and MIBI data. |
| [`immunoinformatics`](bio-skills/immunoinformatics) | 1.0.0 | 5 | MHC binding, neoantigen prediction, and HLA typing. |
| [`liquid-biopsy`](bio-skills/liquid-biopsy) | 1.0.0 | 6 | Cell-free DNA fragmentomics, tumor fraction, and methylation cfDNA. |
| [`long-read-sequencing`](bio-skills/long-read-sequencing) | 1.0.0 | 8 | ONT and PacBio basecalling, alignment, and structural-variant workflows. |
| [`machine-learning`](bio-skills/machine-learning) | 1.0.0 | 8 | Biomarker discovery, model training, and cross-validation pipelines. |
| [`metabolomics`](bio-skills/metabolomics) | 1.0.0 | 8 | Mass-spec metabolite identification, alignment, and quantification. |
| [`metagenomics`](bio-skills/metagenomics) | 1.0.0 | 7 | Shotgun microbial profiling, assembly, and binning. |
| [`methylation-analysis`](bio-skills/methylation-analysis) | 1.0.0 | 5 | Bisulfite alignment and differential methylation testing. |
| [`microbiome`](bio-skills/microbiome) | 1.0.0 | 6 | 16S rRNA amplicon and microbiota community profiling. |
| [`multi-omics-integration`](bio-skills/multi-omics-integration) | 1.0.0 | 4 | Cross-modality fusion: MOFA, DIABLO, WNN, totalVI. |
| [`pathway-analysis`](bio-skills/pathway-analysis) | 1.0.0 | 6 | GO, KEGG, Reactome, and GSEA enrichment testing. |
| [`phasing-imputation`](bio-skills/phasing-imputation) | 1.0.0 | 4 | Haplotype phasing and genotype imputation with SHAPEIT and Beagle. |
| [`phylogenetics`](bio-skills/phylogenetics) | 1.0.0 | 8 | Tree construction with IQ-TREE, RAxML, BEAST, and ancestral state. |
| [`population-genetics`](bio-skills/population-genetics) | 1.0.0 | 6 | GWAS, population structure, LD, and selection scans. |
| [`primer-design`](bio-skills/primer-design) | 1.0.0 | 3 | PCR and qPCR primer generation with Primer3 and primerBLAST. |
| [`proteomics`](bio-skills/proteomics) | 1.0.0 | 9 | Mass-spec quantification and protein abundance pipelines. |
| [`read-alignment`](bio-skills/read-alignment) | 1.0.0 | 4 | Short-read mapping with BWA-MEM2, Bowtie2, STAR, HISAT2. |
| [`read-qc`](bio-skills/read-qc) | 1.0.0 | 7 | FastQC, fastp, trimming, and contamination screening. |
| [`reporting`](bio-skills/reporting) | 1.0.0 | 5 | Reproducible HTML, Quarto, and R Markdown reports. |
| [`restriction-analysis`](bio-skills/restriction-analysis) | 1.0.0 | 4 | Restriction-enzyme mapping and digestion prediction. |
| [`ribo-seq`](bio-skills/ribo-seq) | 1.0.0 | 5 | Ribosome profiling and translation-efficiency analysis. |
| [`rna-quantification`](bio-skills/rna-quantification) | 1.0.0 | 4 | Gene and transcript abundance with Salmon, kallisto, RSEM. |
| [`rna-structure`](bio-skills/rna-structure) | 1.0.0 | 3 | Secondary-structure prediction with RNAfold, IPknot. |
| [`sequence-io`](bio-skills/sequence-io) | 1.0.0 | 9 | FASTA/FASTQ parsing, conversion, and indexing. |
| [`sequence-manipulation`](bio-skills/sequence-manipulation) | 1.0.0 | 7 | Transcription, translation, ORF finding, and motif search. |
| [`single-cell`](bio-skills/single-cell) | 1.0.0 | 14 | scRNA-seq clustering, annotation, trajectory, and integration. |
| [`small-rna-seq`](bio-skills/small-rna-seq) | 1.0.0 | 5 | miRNA, piRNA, and small-RNA quantification. |
| [`spatial-transcriptomics`](bio-skills/spatial-transcriptomics) | 1.0.0 | 11 | Visium, Slide-seq, and high-resolution tissue expression. |
| [`structural-biology`](bio-skills/structural-biology) | 1.0.0 | 8 | PDB parsing, AlphaFold, ESMFold, and structure analysis. |
| [`systems-biology`](bio-skills/systems-biology) | 1.0.0 | 5 | Metabolic flux balance, kinetic modelling, network analysis. |
| [`tcr-bcr-analysis`](bio-skills/tcr-bcr-analysis) | 1.0.0 | 5 | Immune-receptor repertoire profiling and clonal-family analysis. |
| [`temporal-genomics`](bio-skills/temporal-genomics) | 1.0.0 | 5 | Time-series and circadian expression analysis. |
| [`variant-calling`](bio-skills/variant-calling) | 1.0.0 | 13 | SNPs, indels, SVs with GATK, DeepVariant, Manta, Delly. |
| [`workflow-management`](bio-skills/workflow-management) | 1.0.0 | 5 | Snakemake, Nextflow, CWL, WDL pipeline scaffolding. |
| [`workflows`](bio-skills/workflows) | 1.0.0 | 41 | Ready-to-run analysis pipelines combining multiple skills. |
<!-- catalog:end biomedical -->

---

## Moved and retired

A skill that was merged into another, or retired, keeps its release: its archive is replaced by a short stub with the same name that tells the model which skill to use instead and tells the person how to add it from BAAM. An installed old copy keeps working until it is removed.

<!-- catalog:begin moved -->
Nothing has moved or retired yet.
<!-- catalog:end moved -->

---

## The catalog

[`catalog.json`](catalog.json) is the source of truth for every BAAM skill and bundle. Each row records the item's id, display name, category, folder, version, status (`active`, `superseded_by:<id>`, `superseded_by:builtin:<name>` or `retired`), former names (`aliases`), the one job it owns (`job`, a dotted `<domain>.<task>` key), written boundaries to look-alike items (`distinct_from`), its sources and their licences, the licence of its archive, its notice file, its release and its history. A bundle's row also lists its components, each with its pinned `name` and its own job.

The checks run with Node and no dependencies:

```bash
node scripts/check-catalog.mjs              # folders, frontmatter, versions, licences, notices, stubs, D2, D3, D5, D6
node scripts/check-catalog.mjs --jobs <biorouter>/landing/catalog/jobs.json \
  --extensions <biorouter>/landing/catalog/extensions.json   # plus D1, D4 and G1 across both catalogs
node scripts/render-readme.mjs --check      # README tables and NOTICE match the catalog
node scripts/write-stubs.mjs --check        # merged and retired folders hold their generated stub
node --test scripts/                        # the checks' own tests
```

The duplicate rules: **D1**, no two active items own the same job, and none claims a job Biorouter itself owns. **D2**, ids, display names, aliases and Biorouter's built-in names share one namespace. **D3**, two active items whose name, summary, keywords and description look alike (token-set Jaccard at or above the threshold in `scripts/lib/catalog-rules.mjs`) either merge or record a `distinct_from` boundary. **D4**, a merged item points at an active item that lists the old id in `aliases`. **D5**, component names are unique, and look-alike components across bundles record a boundary. **D6**, no active skill is a template shell, more than half of whose lines appear in five or more other skills. **G1**, every required job in the extension site's `jobs.json` has an owner or a plan. Rule failures that exist when a rule lands are listed in `baseline_violations`, each owned by the work package that removes it.

To change a skill: edit its folder, raise `version` in its row and `metadata.version` in every `SKILL.md` of the item (a fix is a patch, new content a minor version), add a `history` entry, and run the checks. To merge one skill into another: add the old id to the target's `aliases`, set the old row's `status` to `superseded_by:<target>`, raise its version, and run `node scripts/write-stubs.mjs`. To retire one: set `status` to `retired` with `retired.reason` (and `retired.use` when something replaces it), raise the version, and run the same script. `node scripts/build-zip.mjs <id>` builds an archive, `node scripts/verify-release.mjs <id>` compares a published archive with its folder, `node scripts/upstream-drift.mjs` reports upstreams that moved, and `node scripts/release.mjs <id>` prints the release steps (`--execute` runs them).

---

## Repository layout

```
biorouter-skills/
├── catalog.json                 every skill and bundle, active or not
├── builtin-skill-names.json     names Biorouter ships (scripts/builtin-names.mjs)
├── LICENSE                      Apache-2.0, for material written here
├── NOTICE                       upstream attribution, generated from the catalog
├── scripts/                     checks, archive builder, release tools and their tests
├── <skill-id>/SKILL.md          one folder per single skill, with any supporting files
├── superpowers/<skill>/SKILL.md a bundle: one folder per component
└── bio-skills/<bundle>/<skill>/SKILL.md
```

Every `SKILL.md` has YAML frontmatter with `name`, `description`, `license`, optional `user-invocable`, and a `metadata` map with `version` (and, for adapted skills, `upstream`).

---

## Contributing a skill

1. Fork this repository and add a top-level folder named after the skill (kebab-case).
2. Write its `SKILL.md`:

   ```markdown
   ---
   name: my-skill
   description: One sentence on what it does and when to use it. The model reads this line to decide whether to load the skill.
   license: Apache-2.0
   user-invocable: true
   metadata:
     version: "1.0.0"
   ---

   # My Skill

   The body. Be concrete, give examples, and keep it to one job.
   ```

3. Add its row to `catalog.json` with a job no other item owns, run the checks, and open a pull request. A maintainer cuts the `skill-<id>` release.

---

## Sources and attribution

Licence per skill, as the catalog records. Material written here is Apache-2.0; adapted material keeps its upstream licence, and each such archive carries the upstream copyright line and licence text. Lab-original skills are written by the [Baranzini Lab](https://baranzinilab.ucsf.edu/).

<!-- catalog:begin sources -->
| Skills | Source | Licence of the archive | What changed for Biorouter |
|---|---|---|---|
| `scientific-research`, `anti-ai-writing`, `ggplot-visualization`, `r-scripting`, `python-scripting`, `ucsf-hpc`, `develop-biorouter-extension` | Lab-original | Apache-2.0 | — |
| 31 skills: `empirical-research-router`, `causal-identification-gates`, `replication-package-audit`, `claim-evidence-integrity`, `empirical-benchmark-harness`, `scientific-artifacts`, `open-science-review`, `scientific-data-engineering`, `statistical-modeling-bayes`, `scientific-machine-learning`, `geospatial-science`, `neurophysiology-analysis`, `quantum-scientific-computing`, `materials-informatics`, `biomedical-imaging-pathology`, `citation-library-management`, `laboratory-automation-planning`, `econometrics-toolkit`, `systematic-review-prisma`, `simulation-optimization`, `physical-science-computing`, `metabolic-modeling-cobrapy`, `drug-discovery-benchmarks`, `clinical-decision-support-review`, `scientific-visual-communication`, `grant-funding-strategy`, `regulatory-quality-systems`, `gpu-compute-optimization`, `research-evaluation-venues`, `qualitative-thematic-analysis`, `financial-accounting-econometrics` | Native rewrite inspired by [brycewang-stanford/Auto-Empirical-Research-Skills](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills) and [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills); no upstream text copied | Apache-2.0 | — |
| `citation-temporal-integrity`, `stata-research-workbench`, `survey-weights-complex-samples`, `psychometrics-sem-measurement`, `social-science-text-as-data`, `econ-finance-data-sources`, `empirical-paper-submission-rr`, `structural-economics-theory`, `causal-heterogeneity-policy-learning` | Native rewrite inspired by [brycewang-stanford/Auto-Empirical-Research-Skills](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills); no upstream text copied | Apache-2.0 | — |
| `taste-skill` | [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) (MIT) | Apache-2.0 | Wired to auto-trigger on frontend work; attribution header kept. |
| `autoskill-workflow-discovery`, `arbor-optimization`, `hugging-science-resource-discovery`, `molecular-dynamics`, `general-time-series-forecasting`, `bids-neuroimaging`, `clinical-ai-modeling`, `computational-fluid-dynamics` | Native rewrite inspired by [K-Dense-AI/scientific-agent-skills](https://github.com/K-Dense-AI/scientific-agent-skills); no upstream text copied | Apache-2.0 | — |
| `ralph` | [snarktank/ralph](https://github.com/snarktank/ralph) (MIT) | Apache-2.0 | PRD and prd.json flow reworked around the Biorouter agent loop and /ralph. |
| `superpowers` | [obra/superpowers](https://github.com/obra/superpowers) (MIT) | Apache-2.0 | Folded 13 of the 15 skills in; dropped the using-superpowers dispatcher and its SessionStart hook; optional Stop-hook recipes added. |
| `code-review`, `code-simplifier`, `commit-commands`, `skill-creator`, `code-modernization`, `playground`, `frontend-design` | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) (Apache-2.0) | Apache-2.0 | The plugin's commands and subagents folded into one SKILL.md; shell routed through the Developer extension. |
| `hookify` | [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) (Apache-2.0) | Apache-2.0 | Rewritten to write enforced Biorouter hooks in <project>/.biorouter/hooks.yaml. |
| 63 bundles: `alignment`, `alignment-files`, `alternative-splicing`, `atac-seq`, `causal-genomics`, `chemoinformatics`, `chip-seq`, `clinical-biostatistics`, `clinical-databases`, `clip-seq`, `comparative-genomics`, `copy-number`, `crispr-screens`, `data-visualization`, `database-access`, `differential-expression`, `ecological-genomics`, `epidemiological-genomics`, `epitranscriptomics`, `experimental-design`, `expression-matrix`, `flow-cytometry`, `gene-regulatory-networks`, `genome-annotation`, `genome-assembly`, `genome-engineering`, `genome-intervals`, `hi-c-analysis`, `imaging-mass-cytometry`, `immunoinformatics`, `liquid-biopsy`, `long-read-sequencing`, `machine-learning`, `metabolomics`, `metagenomics`, `methylation-analysis`, `microbiome`, `multi-omics-integration`, `pathway-analysis`, `phasing-imputation`, `phylogenetics`, `population-genetics`, `primer-design`, `proteomics`, `read-alignment`, `read-qc`, `reporting`, `restriction-analysis`, `ribo-seq`, `rna-quantification`, `rna-structure`, `sequence-io`, `sequence-manipulation`, `single-cell`, `small-rna-seq`, `spatial-transcriptomics`, `structural-biology`, `systems-biology`, `tcr-bcr-analysis`, `temporal-genomics`, `variant-calling`, `workflow-management`, `workflows` | [GPTomics/bioSkills](https://github.com/GPTomics/bioSkills) (MIT) | Apache-2.0 | Dropped the bio- name prefix, set user-invocable: false, added a one-line uv tip to skills that ship pip install commands. |
<!-- catalog:end sources -->

Maintained by the [Baranzini Lab](https://baranzinilab.ucsf.edu/) at UCSF.
