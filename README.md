# Biorouter Skills

The **skills** of [BAAM](https://biorouter.ucsf.edu/baam.html), the marketplace of [Biorouter](https://github.com/BaranziniLab/biorouter), UCSF's local-first AI workspace for biomedical research.

Skills are instruction bundles that Biorouter loads on demand to shape how the model writes code, drafts documents, reasons about a problem and runs research. Some load automatically when a task matches their description; others are *user-invocable* and answer a slash command such as `/scientific-research` in the chat.

This repository is curated and organized by Wanjun Gu at the [Baranzini Lab](https://baranzinilab.ucsf.edu/), UCSF. Each top-level folder is one skill or a bundle of skills, `bio-skills/<id>/` holds the biomedical bundles, and [`catalog.json`](catalog.json) records every item, active or not.

<!-- catalog:begin counts -->
58 core skills, 12 developer skills and 63 biomedical bundles (570 skills) are active; 12 older skills have moved or retired.
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
| [`scientific-research`](scientific-research) | 1.1.0 | `/scientific-research` | Apache-2.0 | End-to-end research: scopes the question, reviews real literature, generates hypotheses, plans and verifies the analysis, then writes a cited draft. Delegates biomedical data queries to whichever data extensions are installed. It never fabricates a citation or result. |
| [`empirical-research-router`](empirical-research-router) | 1.1.0 | `/empirical-research-router` | Apache-2.0 | Stage-gated empirical research workflow: design register, data audit, identification, estimation, robustness, replication, and reporting. |
| [`causal-identification-gates`](causal-identification-gates) | 1.1.0 | `/causal-identification-gates` | Apache-2.0 | Audits whether RCT, observational, IV, RDD, DiD, synthetic-control, matching, DML, or survival designs support causal language. |
| [`replication-package-audit`](replication-package-audit) | 1.1.0 | `/replication-package-audit` | Apache-2.0 AND MIT AND BSD-3-Clause AND CC-BY-4.0 AND CC0-1.0 | Checks research packages for clean-run reproducibility, relative paths, environment capture, seeds, logs, and table/figure mapping. |
| [`claim-evidence-integrity`](claim-evidence-integrity) | 1.1.0 | `/claim-evidence-integrity` | Apache-2.0 AND MIT | Verifies that manuscript claims, numbers, citations, figures, and tables are grounded in traceable evidence. |
| [`empirical-benchmark-harness`](empirical-benchmark-harness) | 1.1.0 | `/empirical-benchmark-harness` | Apache-2.0 | Known-answer benchmark patterns for testing whether empirical-analysis agents avoid common causal and reproducibility failures. |
| [`scientific-artifacts`](scientific-artifacts) | 1.1.0 | `/scientific-artifacts` | Apache-2.0 AND MIT AND CC0-1.0 | Plans and verifies DOCX/PDF/PPTX/XLSX/LaTeX/scientific figure artifacts with source-to-exhibit mapping. |
| [`scientific-data-engineering`](scientific-data-engineering) | 1.1.0 | `/scientific-data-engineering` | Apache-2.0 AND MIT AND BSD-3-Clause | Plans scalable scientific data workflows with Polars, Dask, Zarr, TileDB, Arrow/Parquet, HDF5, and dataset versioning. |
| [`statistical-modeling-bayes`](statistical-modeling-bayes) | 1.1.0 | `/statistical-modeling-bayes` | Apache-2.0 AND MIT AND BSD-3-Clause | Designs and critiques statistical, Bayesian, survival, hierarchical, power, and uncertainty-reporting workflows. |
| [`scientific-machine-learning`](scientific-machine-learning) | 1.1.0 | `/scientific-machine-learning` | Apache-2.0 AND MIT AND BSD-3-Clause | Plans scientific ML with leakage checks, transformers, graph neural networks, active learning, SHAP, and reproducibility gates. |
| [`geospatial-science`](geospatial-science) | 1.1.0 | `/geospatial-science` | Apache-2.0 AND MIT | Handles geospatial analysis with CRS checks, spatial joins, rasters/vectors, maps, and spatial statistics. |
| [`neurophysiology-analysis`](neurophysiology-analysis) | 1.1.0 | `/neurophysiology-analysis` | Apache-2.0 AND MIT | Plans biosignal and neural-recording analysis: ECG/EDA/PPG, spike sorting, Neuropixels metadata, and peri-event QC. |
| [`quantum-scientific-computing`](quantum-scientific-computing) | 1.1.0 | `/quantum-scientific-computing` | Apache-2.0 AND MIT | Routes quantum and scientific simulation work across Qiskit, Cirq, PennyLane, QuTiP, and validation checks. |
| [`materials-informatics`](materials-informatics) | 1.1.0 | `/materials-informatics` | Apache-2.0 AND MIT | Guides computational materials workflows with structures, crystals, compositions, phase diagrams, and dataset provenance. |
| [`biomedical-imaging-pathology`](biomedical-imaging-pathology) | 1.1.0 | `/biomedical-imaging-pathology` | Apache-2.0 AND MIT | Plans DICOM/pathology/PACS workflows with tiling, metadata, QC, cohort provenance, and privacy-safe reporting. |
| [`citation-library-management`](citation-library-management) | 1.1.0 | `/citation-library-management` | Apache-2.0 AND MIT | Builds, cleans, verifies, and deduplicates Zotero/BibTeX/RIS/CSL citation libraries. |
| [`laboratory-automation-planning`](laboratory-automation-planning) | 1.1.0 | `/laboratory-automation-planning` | Apache-2.0 AND MIT | Plans Opentrons/cloud-lab workflows with plate maps, protocol simulation, sample metadata, and execution gates. |
| [`econometrics-toolkit`](econometrics-toolkit) | 1.1.0 | `/econometrics-toolkit` | Apache-2.0 AND BSD-3-Clause | Plans applied econometrics in Python, R, or Stata: panel data, IV, DiD, RDD, clustering, and replication tables. |
| [`systematic-review-prisma`](systematic-review-prisma) | 1.1.0 | `/systematic-review-prisma` | Apache-2.0 AND MIT | Runs systematic-review workflows: PICO, search strings, screening logs, PRISMA flow, extraction, risk of bias, and synthesis. |
| [`simulation-optimization`](simulation-optimization) | 1.1.0 | `/simulation-optimization` | Apache-2.0 AND MIT | Plans discrete-event simulation, multi-objective optimization, sensitivity analysis, scheduling, and what-if modeling. |
| [`physical-science-computing`](physical-science-computing) | 1.1.0 | `/physical-science-computing` | Apache-2.0 AND MIT AND BSD-3-Clause | Routes astronomy, physics, units, coordinate systems, spectra, numerical experiments, and physical-science workflows. |
| [`clinical-decision-support-review`](clinical-decision-support-review) | 1.1.0 | `/clinical-decision-support-review` | Apache-2.0 AND MIT | Reviews clinical decision support, treatment plans, and reports for evidence grounding, safety scope, and no-PHI handling. |
| [`grant-funding-strategy`](grant-funding-strategy) | 1.1.0 | `/grant-funding-strategy` | Apache-2.0 AND MIT | Structures research grants, specific aims, milestones, reviewer-risk responses, and funder-fit checks. |
| [`regulatory-quality-systems`](regulatory-quality-systems) | 1.1.0 | `/regulatory-quality-systems` | Apache-2.0 AND MIT | Reviews scientific software, device, and lab processes against quality, validation, traceability, and design-control gates. |
| [`gpu-compute-optimization`](gpu-compute-optimization) | 1.1.0 | `/gpu-compute-optimization` | Apache-2.0 AND MIT | Plans GPU-bound training/inference, batching, profiling, memory pressure, mixed precision, and reproducible compute. |
| [`research-evaluation-venues`](research-evaluation-venues) | 1.1.0 | `/research-evaluation-venues` | Apache-2.0 AND MIT | Evaluates papers, scholars, venues, impact claims, reviewer fit, and publication positioning. |
| [`qualitative-thematic-analysis`](qualitative-thematic-analysis) | 1.1.0 | `/qualitative-thematic-analysis` | Apache-2.0 | Plans qualitative coding, thematic analysis, codebooks, memoing, inter-rater checks, and audit trails. |
| [`survey-weights-complex-samples`](survey-weights-complex-samples) | 1.1.0 | `/survey-weights-complex-samples` | Apache-2.0 | Handles complex survey designs with strata, PSUs, replicate weights, domain analysis, calibration, and weighted inference. |
| [`psychometrics-sem-measurement`](psychometrics-sem-measurement) | 1.1.0 | `/psychometrics-sem-measurement` | Apache-2.0 | Plans reliability, CFA/SEM, mediation/moderation, invariance, item analysis, and APA-style measurement reporting. |
| [`social-science-text-as-data`](social-science-text-as-data) | 1.1.0 | `/social-science-text-as-data` | Apache-2.0 | Plans dictionaries, topic models, embeddings, sentiment, supervised coding, LLM-label validation, and measurement-error checks. |
| [`empirical-paper-submission-rr`](empirical-paper-submission-rr) | 1.1.0 | `/empirical-paper-submission-rr` | Apache-2.0 | Plans journal targeting, referee reports, response letters, revise-and-resubmit execution, and appendix organization. |
| [`causal-heterogeneity-policy-learning`](causal-heterogeneity-policy-learning) | 1.1.0 | `/causal-heterogeneity-policy-learning` | Apache-2.0 | Plans CATE, causal forests, meta-learners, policy learning, conformal causal inference, fairness, and subgroup reporting. |
| [`autoskill-workflow-discovery`](autoskill-workflow-discovery) | 1.1.0 | `/autoskill-workflow-discovery` | Apache-2.0 | Detects repeated workflows and drafts native Biorouter skills, hooks, checklist updates, or extension plans. |
| [`arbor-optimization`](arbor-optimization) | 1.1.0 | `/arbor-optimization` | Apache-2.0 | Runs evaluator-driven branch-and-prune exploration for improving research artifacts, prompts, analyses, and designs. |
| [`hugging-science-resource-discovery`](hugging-science-resource-discovery) | 1.1.0 | `/hugging-science-resource-discovery` | Apache-2.0 | Finds and evaluates Hugging Face scientific models, datasets, Spaces, and papers with license and provenance checks. |
| [`molecular-dynamics`](molecular-dynamics) | 1.1.0 | `/molecular-dynamics` | Apache-2.0 | Plans MD setup and trajectory analysis with OpenMM, GROMACS, AmberTools, MDAnalysis, MDTraj, and reproducibility checks. |
| [`general-time-series-forecasting`](general-time-series-forecasting) | 1.1.0 | `/general-time-series-forecasting` | Apache-2.0 | Plans non-omics forecasting with classical models, ML, foundation models, backtesting, leakage checks, and uncertainty. |
| [`bids-neuroimaging`](bids-neuroimaging) | 1.1.0 | `/bids-neuroimaging` | Apache-2.0 | Audits BIDS neuroimaging datasets, derivatives, validation, metadata, and reproducible preprocessing readiness. |
| [`clinical-ai-modeling`](clinical-ai-modeling) | 1.1.0 | `/clinical-ai-modeling` | Apache-2.0 | Plans clinical AI modeling workflows with EHR cohorts, validation, bias checks, calibration, safety, and no-PHI handling. |
| [`computational-fluid-dynamics`](computational-fluid-dynamics) | 1.1.0 | `/computational-fluid-dynamics` | Apache-2.0 | Plans CFD workflows with meshes, boundary conditions, turbulence models, solver validation, and convergence checks. |
| [`anti-ai-writing`](anti-ai-writing) | 1.1.0 | `/anti-ai-writing` | Apache-2.0 | A pass/fail checklist for spotting AI writing patterns before generating prose, articles, or essays. |
| [`ggplot-visualization`](ggplot-visualization) | 1.1.0 | Auto | Apache-2.0 AND MIT | Applies ggplot2 best-practice style when writing R plotting code. |
| [`r-scripting`](r-scripting) | 1.1.0 | Auto | Apache-2.0 | Applies tidyverse conventions and documentation standards when writing or reviewing R code. |
| [`python-scripting`](python-scripting) | 1.1.0 | Auto | Apache-2.0 | Applies Python naming, typing, error handling, and project structure conventions when writing Python code. |
| [`ralph`](ralph) | 1.1.0 | `/ralph` | Apache-2.0 AND MIT | End-to-end planning for the Ralph autonomous agent loop. Drafts a markdown PRD from a feature idea, then converts it to prd.json. Each story is sized for one hands-off iteration. |
| [`superpowers`](superpowers) | 1.1.0 | Bundle, 13 skills | Apache-2.0 AND MIT | Engineering discipline skills: brainstorming, TDD, systematic debugging, parallel agents, plan writing, code review, git worktrees. Workflows tested on long-running engineering tasks. |
| [`ucsf-hpc`](ucsf-hpc) | 1.1.0 | `/ucsf-hpc` | Apache-2.0 | SSH setup, SLURM job templates (CPU/GPU/H200), file transfer, module management, and common pitfalls for the UCSF CHPC cluster. |
| [`exploratory-data-analysis`](exploratory-data-analysis) | 1.0.0 | Auto | Apache-2.0 AND MIT |  |
| [`figure-qa`](figure-qa) | 1.0.0 | Auto | Apache-2.0 AND MIT AND BSD-3-Clause |  |
| [`interactive-dashboards`](interactive-dashboards) | 1.0.0 | Bundle, 5 skills | Apache-2.0 AND MIT |  |
| [`manuscript-peer-review`](manuscript-peer-review) | 1.0.0 | Auto | Apache-2.0 AND MIT |  |
| [`microscopy-image-analysis`](microscopy-image-analysis) | 1.0.0 | Auto | Apache-2.0 AND MIT |  |
| [`python-visualization`](python-visualization) | 1.0.0 | Auto | Apache-2.0 AND MIT |  |
| [`science-superpowers`](science-superpowers) | 1.0.0 | Bundle, 12 skills | Apache-2.0 AND MIT |  |
| [`scientific-manuscript-writing`](scientific-manuscript-writing) | 1.0.0 | Auto | Apache-2.0 AND MIT |  |
| [`scientific-problem-selection`](scientific-problem-selection) | 1.0.0 | Auto | Apache-2.0 |  |
| [`scientific-prose-review`](scientific-prose-review) | 1.0.0 | Auto | CC-BY-4.0 |  |
| [`phi-deidentification`](phi-deidentification) | 1.0.1 | Auto | Apache-2.0 AND MIT | De-identifies clinical CSV, TSV and Excel tables under HIPAA Safe Harbor with a local script that makes no network calls; the agent never reads the raw data. |
<!-- catalog:end core -->

---

## Developer and authoring skills

Several of these are adapted from [Anthropic's official Claude Code plugins](https://github.com/anthropics/claude-plugins-official) (Apache-2.0). Biorouter has no loader for plugin commands or subagents, so each plugin is folded into one self-contained `SKILL.md`. `hookify` writes real, enforced hooks in `<project>/.biorouter/hooks.yaml`.

<!-- catalog:begin developer -->
| Skill | Version | Invocation | Licence | What it does |
|---|---|---|---|---|
| [`code-review`](code-review) | 1.1.0 | `/code-review` | Apache-2.0 AND MIT | Multi-stage, confidence-scored review of a pull request or local diff. Drops low-confidence findings and posts a formatted PR comment via gh. |
| [`code-simplifier`](code-simplifier) | 1.1.1 | `/code-simplifier` | Apache-2.0 | Simplifies recently-changed code for clarity and consistency while preserving exact behavior. Defers language style to the Python and R skills. |
| [`commit-commands`](commit-commands) | 1.1.0 | `/commit-commands` | Apache-2.0 | Three git workflows: a clean single commit; commit + push + open a PR; and cleanup of [gone] branches and their worktrees. |
| [`hookify`](hookify) | 1.1.0 | `/hookify` | Apache-2.0 | Turns project guardrails (warn/block rules) into real Biorouter hooks in .biorouter/hooks.yaml. A block rule stops the action; a warn rule shows a notice. Requires allow_project_hooks: true. |
| [`code-modernization`](code-modernization) | 1.1.0 | `/code-modernization` | Apache-2.0 AND MIT | Phased legacy-modernization workflow (preflight, assess, map, extract rules, brief, transform, harden, status) for COBOL, legacy Java/C++, and monoliths. |
| [`playground`](playground) | 1.1.1 | `/playground` | Apache-2.0 | Generates self-contained single-file interactive HTML playgrounds for configuring something visually, then copying out a ready-to-use prompt. |
| [`frontend-design`](frontend-design) | 1.1.0 | Auto | Apache-2.0 AND MIT | Anthropic's anti-slop frontend guidance for distinctive, production-grade UIs. Complements the Taste skill above. |
| [`high-performance-r`](high-performance-r) | 1.0.0 | Auto | Apache-2.0 |  |
| [`julia-development`](julia-development) | 1.0.0 | Bundle, 12 skills | Apache-2.0 AND MIT |  |
| [`r-package-development`](r-package-development) | 1.0.0 | Bundle, 8 skills | Apache-2.0 AND MIT |  |
| [`research-code-hardening`](research-code-hardening) | 1.0.0 | Auto | Apache-2.0 AND BSD-3-Clause |  |
| [`scientific-python-development`](scientific-python-development) | 1.0.0 | Bundle, 5 skills | Apache-2.0 AND BSD-3-Clause |  |
<!-- catalog:end developer -->

---

## Biomedical bundles

[`bio-skills/`](bio-skills) holds bundles that load automatically when Biorouter sees a relevant file or task (a `.vcf`, a `scanpy` import, a Seurat object). They come from [GPTomics/bioSkills](https://github.com/GPTomics/bioSkills) (MIT) plus Biorouter-original additions. Biorouter prefers [`uv`](https://github.com/astral-sh/uv) over `pip`; skills with `pip install` lines carry a one-line uv tip and keep the original commands. See [`bio-skills/INDEX.md`](bio-skills/INDEX.md) for every skill.

<!-- catalog:begin biomedical -->
| Bundle | Version | Skills | What it covers |
|---|---|---|---|
| [`alignment`](bio-skills/alignment) | 1.1.0 | 7 | Multiple sequence alignment and pairwise alignment. |
| [`alignment-files`](bio-skills/alignment-files) | 1.1.0 | 10 | SAM/BAM/CRAM manipulation, sorting, indexing, dedup, and stats. |
| [`alternative-splicing`](bio-skills/alternative-splicing) | 1.1.0 | 9 | RNA isoform and splice-junction analysis from short- and long-read data. |
| [`atac-seq`](bio-skills/atac-seq) | 1.1.0 | 12 | Chromatin accessibility, peak calling, footprinting, and deep-learning ATAC. |
| [`causal-genomics`](bio-skills/causal-genomics) | 1.1.0 | 11 | Mendelian randomization, colocalization, fine-mapping, and TWAS. |
| [`chemoinformatics`](bio-skills/chemoinformatics) | 1.1.0 | 20 | Molecular structure handling, descriptors, and drug-discovery utilities. |
| [`chip-seq`](bio-skills/chip-seq) | 1.1.0 | 12 | Transcription-factor and histone-mark peak calling and differential binding. |
| [`clinical-biostatistics`](bio-skills/clinical-biostatistics) | 1.1.0 | 15 | Survival, mixed models, and clinical-trial statistical analysis. |
| [`clinical-databases`](bio-skills/clinical-databases) | 1.1.0 | 12 | ClinVar, OMIM, COSMIC, gnomAD, and phenotype DB queries. |
| [`clip-seq`](bio-skills/clip-seq) | 1.1.0 | 12 | Protein-RNA interaction mapping from iCLIP/eCLIP/PAR-CLIP data. |
| [`comparative-genomics`](bio-skills/comparative-genomics) | 1.1.0 | 13 | Cross-species synteny, orthology, and selection scans. |
| [`copy-number`](bio-skills/copy-number) | 1.1.0 | 11 | CNV detection, visualization, and segmentation. |
| [`crispr-screens`](bio-skills/crispr-screens) | 1.1.0 | 15 | Pooled screen counting, MAGeCK analysis, and hit prioritization. |
| [`data-visualization`](bio-skills/data-visualization) | 1.1.0 | 18 | Publication-quality plots: heatmaps, volcano, Manhattan, dimplots. |
| [`database-access`](bio-skills/database-access) | 1.1.0 | 17 | NCBI, UniProt, Ensembl, and biological database APIs. |
| [`differential-expression`](bio-skills/differential-expression) | 1.1.0 | 7 | RNA-seq DE testing with DESeq2, edgeR, and limma-voom. |
| [`ecological-genomics`](bio-skills/ecological-genomics) | 1.1.0 | 6 | Environmental DNA, ecological population genomics, and biodiversity. |
| [`epidemiological-genomics`](bio-skills/epidemiological-genomics) | 1.1.0 | 5 | Pathogen typing, outbreak phylogeography, and surveillance. |
| [`epitranscriptomics`](bio-skills/epitranscriptomics) | 1.1.0 | 5 | m6A and other RNA modification detection from sequencing. |
| [`experimental-design`](bio-skills/experimental-design) | 1.1.0 | 5 | Power analysis and sample-size calculation for omics studies. |
| [`expression-matrix`](bio-skills/expression-matrix) | 1.1.0 | 5 | Count normalization, gene ID mapping, and matrix QC. |
| [`flow-cytometry`](bio-skills/flow-cytometry) | 1.1.0 | 8 | FCS parsing, gating, and high-dimensional cytometry analysis. |
| [`gene-regulatory-networks`](bio-skills/gene-regulatory-networks) | 1.1.0 | 6 | TF-target network inference from expression and chromatin data. |
| [`genome-annotation`](bio-skills/genome-annotation) | 1.1.0 | 7 | Gene prediction, repeat masking, and functional annotation. |
| [`genome-assembly`](bio-skills/genome-assembly) | 1.1.0 | 9 | De novo assembly, polishing, and assembly QC. |
| [`genome-engineering`](bio-skills/genome-engineering) | 1.1.0 | 5 | CRISPR guide design, off-target prediction, and editing analysis. |
| [`genome-intervals`](bio-skills/genome-intervals) | 1.1.0 | 8 | BED/GTF arithmetic, overlap, and feature manipulation. |
| [`hi-c-analysis`](bio-skills/hi-c-analysis) | 1.1.0 | 9 | 3D chromatin contacts, TAD calling, and loop detection. |
| [`imaging-mass-cytometry`](bio-skills/imaging-mass-cytometry) | 1.1.0 | 7 | Single-cell spatial proteomics from IMC and MIBI data. |
| [`immunoinformatics`](bio-skills/immunoinformatics) | 1.1.0 | 6 | MHC binding, neoantigen prediction, and HLA typing. |
| [`liquid-biopsy`](bio-skills/liquid-biopsy) | 1.1.0 | 7 | Cell-free DNA fragmentomics, tumor fraction, and methylation cfDNA. |
| [`long-read-sequencing`](bio-skills/long-read-sequencing) | 1.1.0 | 9 | ONT and PacBio basecalling, alignment, and structural-variant workflows. |
| [`machine-learning`](bio-skills/machine-learning) | 1.1.0 | 7 | Biomarker discovery, model training, and cross-validation pipelines. |
| [`metabolomics`](bio-skills/metabolomics) | 1.1.0 | 9 | Mass-spec metabolite identification, alignment, and quantification. |
| [`metagenomics`](bio-skills/metagenomics) | 1.1.0 | 8 | Shotgun microbial profiling, assembly, and binning. |
| [`methylation-analysis`](bio-skills/methylation-analysis) | 1.1.0 | 10 | Bisulfite alignment and differential methylation testing. |
| [`microbiome`](bio-skills/microbiome) | 1.1.0 | 6 | 16S rRNA amplicon and microbiota community profiling. |
| [`multi-omics-integration`](bio-skills/multi-omics-integration) | 1.1.0 | 5 | Cross-modality fusion: MOFA, DIABLO, WNN, totalVI. |
| [`pathway-analysis`](bio-skills/pathway-analysis) | 1.1.0 | 6 | GO, KEGG, Reactome, and GSEA enrichment testing. |
| [`phasing-imputation`](bio-skills/phasing-imputation) | 1.1.0 | 4 | Haplotype phasing and genotype imputation with SHAPEIT and Beagle. |
| [`phylogenetics`](bio-skills/phylogenetics) | 1.1.0 | 8 | Tree construction with IQ-TREE, RAxML, BEAST, and ancestral state. |
| [`population-genetics`](bio-skills/population-genetics) | 1.1.0 | 7 | GWAS, population structure, LD, and selection scans. |
| [`primer-design`](bio-skills/primer-design) | 1.1.0 | 4 | PCR and qPCR primer generation with Primer3 and primerBLAST. |
| [`proteomics`](bio-skills/proteomics) | 1.1.0 | 9 | Mass-spec quantification and protein abundance pipelines. |
| [`read-alignment`](bio-skills/read-alignment) | 1.1.0 | 4 | Short-read mapping with BWA-MEM2, Bowtie2, STAR, HISAT2. |
| [`read-qc`](bio-skills/read-qc) | 1.1.0 | 7 | FastQC, fastp, trimming, and contamination screening. |
| [`reporting`](bio-skills/reporting) | 1.1.0 | 10 | Reproducible HTML, Quarto, and R Markdown reports. |
| [`restriction-analysis`](bio-skills/restriction-analysis) | 1.1.0 | 5 | Restriction-enzyme mapping and digestion prediction. |
| [`ribo-seq`](bio-skills/ribo-seq) | 1.1.0 | 6 | Ribosome profiling and translation-efficiency analysis. |
| [`rna-quantification`](bio-skills/rna-quantification) | 1.1.0 | 4 | Gene and transcript abundance with Salmon, kallisto, RSEM. |
| [`rna-structure`](bio-skills/rna-structure) | 1.1.0 | 4 | Secondary-structure prediction with RNAfold, IPknot. |
| [`sequence-io`](bio-skills/sequence-io) | 1.1.0 | 9 | FASTA/FASTQ parsing, conversion, and indexing. |
| [`sequence-manipulation`](bio-skills/sequence-manipulation) | 1.1.0 | 7 | Transcription, translation, ORF finding, and motif search. |
| [`single-cell`](bio-skills/single-cell) | 1.1.0 | 15 | scRNA-seq clustering, annotation, trajectory, and integration. |
| [`small-rna-seq`](bio-skills/small-rna-seq) | 1.1.0 | 6 | miRNA, piRNA, and small-RNA quantification. |
| [`spatial-transcriptomics`](bio-skills/spatial-transcriptomics) | 1.1.0 | 12 | Visium, Slide-seq, and high-resolution tissue expression. |
| [`structural-biology`](bio-skills/structural-biology) | 1.1.0 | 11 | PDB parsing, AlphaFold, ESMFold, and structure analysis. |
| [`systems-biology`](bio-skills/systems-biology) | 1.1.0 | 7 | Metabolic flux balance, kinetic modelling, network analysis. |
| [`tcr-bcr-analysis`](bio-skills/tcr-bcr-analysis) | 1.1.0 | 6 | Immune-receptor repertoire profiling and clonal-family analysis. |
| [`temporal-genomics`](bio-skills/temporal-genomics) | 1.1.0 | 6 | Time-series and circadian expression analysis. |
| [`variant-calling`](bio-skills/variant-calling) | 1.1.0 | 13 | SNPs, indels, SVs with GATK, DeepVariant, Manta, Delly. |
| [`workflow-management`](bio-skills/workflow-management) | 1.1.0 | 6 | Snakemake, Nextflow, CWL, WDL pipeline scaffolding. |
| [`workflows`](bio-skills/workflows) | 1.1.0 | 41 | Ready-to-run analysis pipelines combining multiple skills. |
<!-- catalog:end biomedical -->

---

## Moved and retired

A skill that was merged into another, or retired, keeps its release: its archive is replaced by a short stub with the same name that tells the model which skill to use instead and tells the person how to add it from BAAM. An installed old copy keeps working until it is removed.

<!-- catalog:begin moved -->
| Old skill | Final version | Status | Use instead |
|---|---|---|---|
| `citation-temporal-integrity` | 1.1.0 | Merged | [`claim-evidence-integrity`](claim-evidence-integrity) |
| `open-science-review` | 1.1.0 | Merged | [`replication-package-audit`](replication-package-audit) |
| `taste-skill` | 1.1.0 | Merged | [`frontend-design`](frontend-design) |
| `metabolic-modeling-cobrapy` | 1.1.0 | Merged | [`systems-biology`](bio-skills/systems-biology) |
| `drug-discovery-benchmarks` | 1.1.0 | Merged | [`chemoinformatics`](bio-skills/chemoinformatics) |
| `scientific-visual-communication` | 1.1.0 | Merged | [`scientific-artifacts`](scientific-artifacts) |
| `financial-accounting-econometrics` | 1.1.0 | Merged | [`econometrics-toolkit`](econometrics-toolkit) |
| `stata-research-workbench` | 1.1.0 | Merged | [`econometrics-toolkit`](econometrics-toolkit) |
| `econ-finance-data-sources` | 1.1.0 | Merged | [`econometrics-toolkit`](econometrics-toolkit) |
| `structural-economics-theory` | 1.1.0 | Retired: it was an empty template, and no permissively licensed source with real content was found | [`econometrics-toolkit`](econometrics-toolkit) |
| `skill-creator` | 1.1.0 | Merged | the built-in `develop-biorouter-skill` skill (update Biorouter) |
| `develop-biorouter-extension` | 1.1.0 | Retired: Biorouter now ships a newer skill of the same name built in | the built-in `develop-biorouter-extension` skill |
<!-- catalog:end moved -->

---

## The catalog

[`catalog.json`](catalog.json) is the source of truth for every BAAM skill and bundle. Each row records the item's id, display name, category, folder, version, status (`active`, `superseded_by:<id>`, `superseded_by:builtin:<name>` or `retired`), former names (`aliases`), the one job it owns (`job`, a dotted `<domain>.<task>` key), written boundaries to look-alike items (`distinct_from`), where it comes from and who made it (`source` and `contributors`), the licence of its archive, its notice file, its release and its history. A bundle's row also lists its components, each with its pinned `name` and its own job.

The checks run with Node and no dependencies:

```bash
node scripts/check-catalog.mjs              # folders, frontmatter, versions, licences, notices, stubs, D2, D3, D5, D6
node scripts/check-catalog.mjs --jobs <biorouter>/landing/catalog/jobs.json \
  --extensions <biorouter>/landing/catalog/extensions.json   # plus D1, D4 and G1 across both catalogs
node scripts/render-readme.mjs --check      # README tables, NOTICE and provenance files match the catalog
node scripts/write-stubs.mjs --check        # merged and retired folders hold their generated stub
node --test scripts/                        # the checks' own tests
```

The duplicate rules: **D1**, no two active items own the same job, and none claims a job Biorouter itself owns. **D2**, ids, display names, aliases and Biorouter's built-in names share one namespace. **D3**, two active items whose name, summary, keywords and description look alike (token-set Jaccard at or above the threshold in `scripts/lib/catalog-rules.mjs`) either merge or record a `distinct_from` boundary. **D4**, a merged item points at an active item that lists the old id in `aliases`. **D5**, component names are unique, and look-alike components across bundles record a boundary. **D6**, no active skill is a template shell, more than half of whose lines appear in five or more other skills. **G1**, every required job in the extension site's `jobs.json` has an owner or a plan. Rule failures that exist when a rule lands are listed in `baseline_violations`, each owned by the work package that removes it.

**Provenance, format 2.** The catalog says `"format": 2`, so every row records its provenance in format 2 (a row of a format 1 catalog is in format 2 when its own `source.format` is 2). Its `source` records an `origin` (`in-house`, `ideas-derived`, `adapted` or `third-party`); `upstreams`, each with its `kind` (`repository`, `package` or `program`, or a publication: `guideline` for a reporting guideline such as STROBE or PRISMA 2020, `paper` for a publication whose text or method the item takes), `repo` or `url` (a publication's `doi` or `url`), `owner` (`external` or `lab`), how it is used (`use`: `text`, `code`, `data`, `bundled`, `bundled-modified`, `dependency`, `launched`, or `hosted` for a program its publisher runs, which an extension forwards calls to; a skill names such a service under `data_and_services` instead), `what` was used and the `files` it became, a `commit` or `version` (a publication is pinned by its citation instead), its `licence` (with `licence_file` false when the source repository has no licence file at its pin, which only the lab's own work may be: the generated files then make no licence claim for it), the verbatim `copyright` line (or null with a `copyright_note` when the licence names no holder; the note, like `changes` and every other text a record shows, is written for readers, and PV13 refuses process wording in it), the `credit` as the source publishes it and any named `people`, `cite` for the citation the source asks for (its `CITATION.cff` preferred citation; required for a publication), `via` for the sources this one draws on (one repository or a list, each another upstream of the row with its own licence and credit), and `upstream_notice` for an Apache-2.0 source with a NOTICE file; `ideas_from`, each with `what`, the `evidence` that no text was taken, and `applies_to` (`current` or `earlier`); `data_and_services`; `references`; `refused_sources`; `changes`; and, on a merged or retired row, `content_moved_to`. `contributors` names the people who made the Biorouter side, co-authors included. A bundle component may add its own `origin`, `licence`, `sources` and `written_for_biorouter` files, and a `history` entry its `origin` and `licence`. Every row was migrated to format 2 in November 2026, so the format 1 origins `native`, `lab` and `adapted` and `inspired_by` are retired.

The provenance rules: **PV1**, a row is in format 2, with one of the four origins and no retired field; **PV2** to **PV5**, the origin agrees with the record (in-house copies nothing from outside and follows no current idea, ideas-derived follows a current idea and copies nothing, adapted and third-party name what they copy or run and what they changed); **PV6**, every source, idea, data entry and reference is complete, a copied or bundled source is pinned (a guideline or paper by its citation), under an allowed licence, with its copyright line or a note, every source a `via` names is in the row with its own licence and credit, and only an extension's source is `hosted`; **PV7**, a notice file carries the licence text and copyright line of every source the item ships, and an Apache source's NOTICE; **PV8**, the row's and each component's licence cover what they ship; **PV9**, the folder's `PROVENANCE.md`, or a stub's credit lines, is the generated one; **PV10**, each `SKILL.md` carries the generated `metadata.origin`, `metadata.credit` and `metadata.curated_by`; **PV11**, a bundle's components name their lineage, and a file written for Biorouter inside a copied component is listed; **PV12**, every row names its contributors and their roles; **PV13**, a credit line fits in 120 characters, no fixed text (the curator line, the lab's line, the lab's copyright line) is written differently, and no text a record shows carries process wording (an owner answer number, a sign-off, a migration or audit step). Their failures that exist when they land are listed in [`provenance-baseline.json`](provenance-baseline.json), not in `catalog.json`, because the catalog is mirrored byte for byte into the Biorouter repository. Each entry is owned by a work package: **PROV-S1**, the migration of its row to format 2, which is done, and **PROV-S4**, the item's generated folder files, which arrive with its next release. Only the rows that existed when the rules landed may be listed there, so a new row passes every rule from its first commit. A provenance entry anywhere else is refused: in `catalog.json`, and in the extension catalog's baseline when the cross-kind check reads it, except an entry for one of the extension catalog's own rows, which the Biorouter repository's check applies.

To change a skill: edit its folder, raise `version` in its row and `metadata.version` in every `SKILL.md` of the item (a fix is a patch, new content a minor version), add a `history` entry, and run the checks. To merge one skill into another: add the old id to the target's `aliases`, set the old row's `status` to `superseded_by:<target>`, raise its version, and run `node scripts/write-stubs.mjs`. To retire one: set `status` to `retired` with `retired.reason` (and `retired.use` when something replaces it), raise the version, and run the same script. `node scripts/render-readme.mjs` rewrites the README tables and `NOTICE`, and, for a row in format 2, the item's `PROVENANCE.md` and the credit keys of its `SKILL.md` files. To release an item whose folder files were deferred, delete its `PROV-S4` entries from `provenance-baseline.json`, raise its patch version with a history entry that records its `origin` and `licence`, and run `node scripts/render-readme.mjs` and `node scripts/write-stubs.mjs`. `node scripts/build-zip.mjs <id>` builds an archive, `node scripts/verify-release.mjs <id>` compares a published archive with its folder, `node scripts/upstream-drift.mjs` reports upstreams that moved, and `node scripts/release.mjs <id>` prints the release steps (`--execute` runs them).

---

## Repository layout

```
biorouter-skills/
├── catalog.json                 every skill and bundle, active or not
├── provenance-baseline.json     provenance rule failures still open, each with its work package
├── builtin-skill-names.json     names Biorouter ships (scripts/builtin-names.mjs)
├── LICENSE                      Apache-2.0, for material written here
├── NOTICE                       upstream attribution and credits, generated from the catalog
├── scripts/                     checks, archive builder, release tools and their tests
├── <skill-id>/SKILL.md          one folder per single skill, with any supporting files
├── <skill-id>/PROVENANCE.md     its sources, ideas and contributors, generated (format 2 rows)
├── <skill-id>/LICENSE-UPSTREAM  copyright lines and licence texts of copied material
├── superpowers/<skill>/SKILL.md a bundle: one folder per component
└── bio-skills/<bundle>/<skill>/SKILL.md
```

Every `SKILL.md` has YAML frontmatter with `name`, `description`, `license`, optional `user-invocable`, and a `metadata` map with `version`. From the item's next release on, `node scripts/render-readme.mjs` also writes `metadata.origin`, `metadata.credit` (the item's credit line) and `metadata.curated_by` (the curator line). Older skills may still carry `upstream`, `upstream_licence` or `upstream_author`; the generator removes the last two, and `upstream` unless it names a source of the row.

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
     origin: "in-house"
     credit: "Made by the Baranzini Lab (Wanjun Gu, UCSF)."
     curated_by: "Curated and organized by Wanjun Gu, Baranzini Lab, UCSF."
   ---

   # My Skill

   The body. Be concrete, give examples, and keep it to one job.
   ```

   The last three `metadata` keys are generated; `node scripts/render-readme.mjs` writes them from the row.

3. Add its row to `catalog.json` with a job no other item owns.
4. Record its provenance in the row, in format 2: `source` with its `origin`, every source with what was used and how, the ideas it follows, and `changes`; and `contributors`, with a role for each person. Material copied from elsewhere also needs a `LICENSE-UPSTREAM` in the folder, with each source's copyright line and licence text, named in `notice_file`. Then run `node scripts/render-readme.mjs`, which writes the item's `PROVENANCE.md` and its `SKILL.md` credit keys.
5. Run the checks and open a pull request. A maintainer cuts the `skill-<id>` release.

---

## Provenance and credits

Every skill and bundle says what it borrowed (text, code, data or ideas), from whom and under which licence, and credits the people behind that work. Each item has one of four origins, decided in this order: **third-party**, outside work kept largely as published, whose line reads "From <source> by <credit> (<licence>), packaged for Biorouter by the Baranzini Lab."; **adapted**, outside text, code or data changed for Biorouter, "Adapted from <source> by <credit> (<licence>)."; **ideas-derived**, written here with no outside text or code but following named outside work, "Made by the Baranzini Lab (Wanjun Gu, UCSF), with ideas from <source> (<credit>)."; and **in-house**, everything else, "Made by the Baranzini Lab (Wanjun Gu, UCSF)." That line is what BAAM and Biorouter show for the item, and every full record ends with the curator line: "Curated and organized by Wanjun Gu, Baranzini Lab, UCSF."

The full record of an item is its `PROVENANCE.md`, generated from the catalog into its folder: each source with its commit or version, licence, credit and what was used, the files written for Biorouter, the ideas, data, services and references it credits, its contributors and its earlier versions. Copyright lines and licence texts of copied material ship in the item's `LICENSE-UPSTREAM` (its `notice_file`), and the archive of an item in format 2 carries this repository's `LICENSE` as `<id>/LICENSE`. An item's folder files arrive with its next release; until then BAAM and the app show its credits from the catalog.

<!-- catalog:begin provenance -->
| Skills | Origin | Sources and credit | Licence |
|---|---|---|---|
| `scientific-research`, `qualitative-thematic-analysis`, `survey-weights-complex-samples`, `psychometrics-sem-measurement`, `social-science-text-as-data`, `empirical-paper-submission-rr`, `causal-heterogeneity-policy-learning`, `anti-ai-writing`, `r-scripting`, `python-scripting` | In-house | Made by the Baranzini Lab (Wanjun Gu, UCSF). | Apache-2.0 |
| `empirical-research-router`, `causal-identification-gates`, `empirical-benchmark-harness` | Ideas-derived | Made by the Baranzini Lab (Wanjun Gu, UCSF), with ideas from Auto-Empirical Research Skills (Bryce Wang, CoPaper.AI). | Apache-2.0 |
| `replication-package-audit` | Adapted | [medsci-skills](https://github.com/Aperivue/medsci-skills) by Aperivue (MIT), [savvy](https://github.com/uw-ssec/savvy) by UW-SSEC, University of Washington (BSD-3-Clause), [AI-research-feedback](https://github.com/claesbackman/AI-research-feedback) by Claes Bäckman (MIT), [STROBE 2007](https://doi.org/10.1371/journal.pmed.0040296) by von Elm E et al. (CC-BY-4.0), [STARD 2015](https://doi.org/10.1136/bmj.h5527) by Bossuyt PM et al. (CC-BY-4.0), [TRIPOD+AI 2024](https://doi.org/10.1136/bmj-2023-078378) by Collins GS et al. (CC-BY-4.0), [PRISMA 2020](https://doi.org/10.1136/bmj.n71) by Page MJ et al. (CC-BY-4.0), [CONSORT 2025](https://doi.org/10.1136/bmj-2024-081123) by Hopewell S et al. (CC-BY-4.0), [SPIRIT 2025](https://doi.org/10.1136/bmj-2024-081477) by Chan AW et al. (CC-BY-4.0), [ARRIVE 2.0](https://doi.org/10.1371/journal.pbio.3000410) by Percie du Sert N et al. (CC0-1.0) | Apache-2.0 AND MIT AND BSD-3-Clause AND CC-BY-4.0 AND CC0-1.0 |
| `claim-evidence-integrity`, `phi-deidentification` | Adapted | [medsci-skills](https://github.com/Aperivue/medsci-skills) by Aperivue (MIT) | Apache-2.0 AND MIT |
| `scientific-artifacts` | Adapted | [diagram-design](https://github.com/cathrynlavery/diagram-design) by Cathryn Lavery (MIT), [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT, Apache-2.0), [agent-project](https://github.com/SuperiorByteWorks-LLC/agent-project) by Superior Byte Works, LLC (Apache-2.0), [Tabler Icons](https://github.com/tabler/tabler-icons) by Paweł Kuna (MIT), [Simple Icons](https://github.com/simple-icons/simple-icons) by Simple Icons Collaborators (CC0-1.0), [log-z/logos](https://github.com/log-z/logos) by log-Z (MIT), [Devicon](https://github.com/devicons/devicon) by konpa (MIT) | Apache-2.0 AND MIT AND CC0-1.0 |
| `scientific-data-engineering` | Adapted | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT, BSD-3-Clause, Apache-2.0) | Apache-2.0 AND MIT AND BSD-3-Clause |
| `statistical-modeling-bayes` | Adapted | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT, BSD-3-Clause, Apache-2.0), [claude-code-r-skills](https://github.com/ab604/claude-code-r-skills) by ab604 (MIT) | Apache-2.0 AND MIT AND BSD-3-Clause |
| `scientific-machine-learning` | Adapted | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (BSD-3-Clause, Apache-2.0, MIT) | Apache-2.0 AND MIT AND BSD-3-Clause |
| `geospatial-science`, `neurophysiology-analysis`, `materials-informatics`, `citation-library-management`, `laboratory-automation-planning`, `clinical-decision-support-review`, `regulatory-quality-systems`, `gpu-compute-optimization`, `research-evaluation-venues` | Adapted | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT) | Apache-2.0 AND MIT |
| `quantum-scientific-computing` | Adapted | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (Apache-2.0, MIT) | Apache-2.0 AND MIT |
| `biomedical-imaging-pathology`, `simulation-optimization` | Adapted | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT, Apache-2.0) | Apache-2.0 AND MIT |
| `econometrics-toolkit` | Adapted | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (BSD-3-Clause) | Apache-2.0 AND BSD-3-Clause |
| `systematic-review-prisma` | Adapted | [medsci-skills](https://github.com/Aperivue/medsci-skills) by Aperivue (MIT), [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT), [BiostatAgent](https://github.com/choxos/BiostatAgent) by Ahmad Sofi-Mahmudi (MIT) | Apache-2.0 AND MIT |
| `physical-science-computing` | Adapted | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT, BSD-3-Clause) | Apache-2.0 AND MIT AND BSD-3-Clause |
| `grant-funding-strategy` | Adapted | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT), [AI-research-feedback](https://github.com/claesbackman/AI-research-feedback) by Claes Bäckman (MIT) | Apache-2.0 AND MIT |
| `autoskill-workflow-discovery`, `arbor-optimization`, `hugging-science-resource-discovery`, `molecular-dynamics`, `general-time-series-forecasting`, `bids-neuroimaging`, `clinical-ai-modeling`, `computational-fluid-dynamics` | Ideas-derived | Made by the Baranzini Lab (Wanjun Gu, UCSF), with ideas from Scientific Agent Skills (K-Dense Inc.). | Apache-2.0 |
| `ggplot-visualization` | Adapted | [llm-r-skills](https://github.com/jsperger/llm-r-skills) by John Sperger (MIT), [ggplot-skills](https://github.com/Broccolito/ggplot-skills) by Baranzini Lab (Wanjun Gu, UCSF) (MIT), [bioSkills](https://github.com/GPTomics/bioSkills) by GPTomics (MIT) | Apache-2.0 AND MIT |
| `ralph` | Adapted | [ralph](https://github.com/snarktank/ralph) by snarktank (MIT) | Apache-2.0 AND MIT |
| `superpowers` | Third-party | [superpowers](https://github.com/obra/superpowers) by Jesse Vincent (MIT) | Apache-2.0 AND MIT |
| `ucsf-hpc` | In-house | Made by the Baranzini Lab (Wanjun Gu, UCSF). Sources: [UCSFHPCAgent](https://github.com/BaranziniLab/UCSFHPCAgent) by Baranzini Lab (Wanjun Gu, UCSF) (Apache-2.0) | Apache-2.0 |
| `code-review` | Adapted | [code-review plugin](https://github.com/anthropics/claude-plugins-official) by Anthropic (Apache-2.0), [posit-dev/skills](https://github.com/posit-dev/skills) by Posit PBC (MIT) | Apache-2.0 AND MIT |
| `code-simplifier` | Adapted | [code-simplifier plugin](https://github.com/anthropics/claude-plugins-official) by Anthropic (Apache-2.0) | Apache-2.0 |
| `commit-commands` | Adapted | [commit-commands plugin](https://github.com/anthropics/claude-plugins-official) by Anthropic (Apache-2.0) | Apache-2.0 |
| `hookify` | Ideas-derived | Made by the Baranzini Lab (Wanjun Gu, UCSF), with ideas from the hookify plugin (Anthropic). | Apache-2.0 |
| `code-modernization` | Adapted | [code-modernization plugin](https://github.com/anthropics/claude-plugins-official) by Anthropic (Apache-2.0), [Mermaid](https://github.com/mermaid-js/mermaid) by Knut Sveidqvist (MIT) | Apache-2.0 AND MIT |
| `playground` | Adapted | [playground plugin](https://github.com/anthropics/claude-plugins-official) by Anthropic (Apache-2.0) | Apache-2.0 |
| `frontend-design` | Adapted | [anthropics/skills](https://github.com/anthropics/skills) by Anthropic (Apache-2.0), [Taste Skill](https://github.com/Leonxlnx/taste-skill) by Leonxlnx (MIT) | Apache-2.0 AND MIT |
| 59 bundles: `alignment`, `alignment-files`, `alternative-splicing`, `atac-seq`, `causal-genomics`, `chemoinformatics`, `chip-seq`, `clinical-databases`, `clip-seq`, `comparative-genomics`, `copy-number`, `crispr-screens`, `data-visualization`, `differential-expression`, `ecological-genomics`, `epidemiological-genomics`, `epitranscriptomics`, `experimental-design`, `expression-matrix`, `flow-cytometry`, `gene-regulatory-networks`, `genome-annotation`, `genome-assembly`, `genome-engineering`, `genome-intervals`, `hi-c-analysis`, `imaging-mass-cytometry`, `immunoinformatics`, `liquid-biopsy`, `long-read-sequencing`, `machine-learning`, `metabolomics`, `metagenomics`, `methylation-analysis`, `microbiome`, `multi-omics-integration`, `pathway-analysis`, `phasing-imputation`, `phylogenetics`, `population-genetics`, `primer-design`, `proteomics`, `read-alignment`, `read-qc`, `restriction-analysis`, `ribo-seq`, `rna-quantification`, `rna-structure`, `sequence-io`, `sequence-manipulation`, `single-cell`, `small-rna-seq`, `spatial-transcriptomics`, `structural-biology`, `systems-biology`, `tcr-bcr-analysis`, `temporal-genomics`, `variant-calling`, `workflows` | Third-party | [bioSkills](https://github.com/GPTomics/bioSkills) by GPTomics (MIT) | Apache-2.0 AND MIT |
| `clinical-biostatistics` | Third-party | [bioSkills](https://github.com/GPTomics/bioSkills) by GPTomics (MIT), [medsci-skills](https://github.com/Aperivue/medsci-skills) by Aperivue (MIT) | Apache-2.0 AND MIT |
| `database-access` | Third-party | [bioSkills](https://github.com/GPTomics/bioSkills) by GPTomics (MIT), [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT) | Apache-2.0 AND MIT |
| `reporting` | Third-party | [bioSkills](https://github.com/GPTomics/bioSkills) by GPTomics (MIT), [posit-dev/skills](https://github.com/posit-dev/skills) by Posit PBC (MIT), [openai/skills](https://github.com/openai/skills) by OpenAI (Apache-2.0), [marimo-team/skills](https://github.com/marimo-team/skills) by marimo (Apache-2.0) | Apache-2.0 AND MIT |
| `workflow-management` | Third-party | [bioSkills](https://github.com/GPTomics/bioSkills) by GPTomics (MIT), [llm-r-skills](https://github.com/jsperger/llm-r-skills) by John Sperger (MIT) | Apache-2.0 AND MIT |
| `exploratory-data-analysis`, `microscopy-image-analysis` | Third-party | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT) | Apache-2.0 AND MIT |
| `figure-qa` | Adapted | [research-skills](https://github.com/neuromechanist/research-skills) by Seyed (Yahya) Shirazi (BSD-3-Clause), [scipilot-figure-skill](https://github.com/Haojae/scipilot-figure-skill) by Haojae (MIT), [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT), [posit-dev/skills](https://github.com/posit-dev/skills) by Posit PBC (MIT) | Apache-2.0 AND MIT AND BSD-3-Clause |
| `high-performance-r` | In-house | Made by the Baranzini Lab (Wanjun Gu, UCSF). Sources: [gptr](https://github.com/Broccolito/gptr) by Baranzini Lab (Wanjun Gu, UCSF) (Apache-2.0) | Apache-2.0 |
| `interactive-dashboards` | Third-party | [posit-dev/skills](https://github.com/posit-dev/skills) by Posit PBC (MIT), [shiny](https://github.com/rstudio/shiny) by Posit Software, PBC (MIT), [Streamlit](https://github.com/streamlit/streamlit) by Streamlit Inc. and Snowflake Inc. (Apache-2.0), [gptr](https://github.com/Broccolito/gptr) by Baranzini Lab (Wanjun Gu, UCSF) (Apache-2.0) | Apache-2.0 AND MIT |
| `julia-development` | Third-party | [claude_config](https://github.com/timholy/claude_config) by Tim Holy (MIT), [DocBrowser.jl](https://github.com/JuliaLang/DocBrowser.jl) by Ian Butterworth, Kristoffer Carlsson and contributors (MIT) | Apache-2.0 AND MIT |
| `manuscript-peer-review` | Third-party | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT), [medsci-skills](https://github.com/Aperivue/medsci-skills) by Aperivue (MIT) | Apache-2.0 AND MIT |
| `python-visualization` | Third-party | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT), [bioSkills](https://github.com/GPTomics/bioSkills) by GPTomics (MIT), [scipilot-figure-skill](https://github.com/Haojae/scipilot-figure-skill) by Haojae (MIT) | Apache-2.0 AND MIT |
| `r-package-development` | Third-party | [posit-dev/skills](https://github.com/posit-dev/skills) by Posit PBC (MIT), [llm-r-skills](https://github.com/jsperger/llm-r-skills) by John Sperger (MIT) | Apache-2.0 AND MIT |
| `research-code-hardening`, `scientific-python-development` | Third-party | [savvy](https://github.com/uw-ssec/savvy) by UW-SSEC, University of Washington (BSD-3-Clause) | Apache-2.0 AND BSD-3-Clause |
| `science-superpowers` | Third-party | [science-superpowers](https://github.com/K-Dense-AI/science-superpowers) by K-Dense, Inc. (MIT) | Apache-2.0 AND MIT |
| `scientific-manuscript-writing` | Third-party | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) by K-Dense Inc. (MIT), [claude_config](https://github.com/timholy/claude_config) by Tim Holy (MIT) | Apache-2.0 AND MIT |
| `scientific-problem-selection` | Third-party | [knowledge-work-plugins](https://github.com/anthropics/knowledge-work-plugins) by Anthropic (Apache-2.0) | Apache-2.0 |
| `scientific-prose-review` | Third-party | [sciwrite](https://github.com/labarba/sciwrite) by Lorena A. Barba (CC-BY-4.0) | CC-BY-4.0 |
<!-- catalog:end provenance -->

Ideas, references and earlier versions each item records:

<!-- catalog:begin provenance-ideas -->
| Skills | Ideas | References | Earlier versions |
|---|---|---|---|
| `empirical-research-router`, `replication-package-audit` | [Auto-Empirical Research Skills](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills) (Bryce Wang, CoPaper.AI) |  |  |
| `causal-identification-gates`, `claim-evidence-integrity`, `empirical-benchmark-harness` | [Auto-Empirical Research Skills](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills) (Bryce Wang, CoPaper.AI); [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.) |  |  |
| `scientific-artifacts` | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.); [Auto-Empirical Research Skills](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills) (Bryce Wang, CoPaper.AI) |  |  |
| `qualitative-thematic-analysis`, `survey-weights-complex-samples`, `psychometrics-sem-measurement`, `social-science-text-as-data`, `empirical-paper-submission-rr`, `causal-heterogeneity-policy-learning` |  |  | Ideas from [Auto-Empirical Research Skills](https://github.com/brycewang-stanford/Auto-Empirical-Research-Skills) (Bryce Wang, CoPaper.AI) |
| `autoskill-workflow-discovery`, `arbor-optimization`, `hugging-science-resource-discovery`, `molecular-dynamics`, `general-time-series-forecasting`, `bids-neuroimaging`, `clinical-ai-modeling`, `computational-fluid-dynamics` | [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.) |  |  |
| `ralph` |  | [the Ralph pattern](https://ghuntley.com/ralph/) (Geoffrey Huntley) |  |
| `hookify` | [the hookify plugin](https://github.com/anthropics/claude-plugins-official/tree/de573bd84695c6657b28f05ffe32c37bb54d1f55/plugins/hookify) (Anthropic) |  |  |
| `chemoinformatics` | `datamol-medchem`: [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.); `deepchem-drug-discovery`: [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.); `ml-docking-rescoring/references/molecular-docking-diffdock.md`: [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.); `molecular-standardization/references/datamol-medchem.md`: [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.); `qsar-modeling/references/deepchem-drug-discovery.md`: [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.) |  |  |
| `data-visualization` | `scientific-python-visualization`: [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.) |  |  |
| `differential-expression` |  | `pydeseq2`: PyDESeq2 (Boris Muzellec, Maria Telenczuk, Vincent Cabeli, Mathieu Andreux; Owkin), DESeq2 (Michael I. Love, Wolfgang Huber, Simon Anders) |  |
| `machine-learning` | `model-explainability-shap`: [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.); `prediction-explanation/references/model-explainability-shap.md`: [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.) | `causal-ml-dml`: EconML (Microsoft Research ALICE, now PyWhy), Double/debiased machine learning (Victor Chernozhukov and colleagues) |  |
| `structural-biology` | `molecular-docking-diffdock`: [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.) | `protein-language-models`: ESM (Alexander Rives, Zeming Lin and colleagues (Meta FAIR)) |  |
| `workflow-management` | `nextflow-nfcore`: [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.); `nf-core-pipelines/references/nextflow-nfcore.md`: [Scientific Agent Skills](https://github.com/K-Dense-AI/scientific-agent-skills) (K-Dense Inc.) |  |  |
| `scientific-prose-review` |  | [Writing in the Sciences](https://www.coursera.org/learn/sciwrite) (Kristin Sainani, Stanford University); [How to construct a Nature summary paragraph](https://www.nature.com/documents/nature-summary-paragraph.pdf) (Springer Nature) |  |
<!-- catalog:end provenance-ideas -->

Curated and organized by Wanjun Gu, Baranzini Lab, UCSF.
