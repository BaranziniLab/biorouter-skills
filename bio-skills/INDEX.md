# BioSkills Index

All 456 skills organized by category. Each link points to the SKILL.md within this bundle.

## Alignment (7)
_Multiple sequence alignment and pairwise alignment_

- [alignment-io](alignment/alignment-io/SKILL.md) — Read, write, and convert multiple sequence alignment files using Biopython Bio.AlignIO.
- [alignment-trimming](alignment/alignment-trimming/SKILL.md) — Trim multiple sequence alignments using ClipKIT, trimAl, BMGE, Divvier, or HMMcleaner with mode selection guidance per downstream goal.
- [alignment-msa-parsing](alignment/msa-parsing/SKILL.md) — Parse and analyze multiple sequence alignments using Biopython.
- [alignment-msa-statistics](alignment/msa-statistics/SKILL.md) — Calculate alignment statistics including sequence identity, conservation scores, substitution matrices, and similarity metrics.
- [alignment-multiple](alignment/multiple-alignment/SKILL.md) — Perform multiple sequence alignment using MAFFT, MUSCLE5, ClustalOmega, or T-Coffee.
- [alignment-pairwise](alignment/pairwise-alignment/SKILL.md) — Perform pairwise sequence alignment using Biopython Bio.Align.PairwiseAligner.
- [alignment-structural](alignment/structural-alignment/SKILL.md) — Align protein structures using Foldseek 3Di, TM-align, US-align, DALI, or Foldmason for structural MSA.

## Alignment Files (10)
_SAM/BAM/CRAM file manipulation and analysis_

- [alignment-amplicon-clipping](alignment-files/alignment-amplicon-clipping/SKILL.md) — Trim PCR primers from aligned reads in amplicon-panel BAMs using samtools ampliconclip.
- [alignment-filtering](alignment-files/alignment-filtering/SKILL.md) — Filter alignments by flags, mapping quality, and regions using samtools view and pysam.
- [alignment-indexing](alignment-files/alignment-indexing/SKILL.md) — Create and use BAI/CSI indices for BAM/CRAM files using samtools and pysam.
- [alignment-sorting](alignment-files/alignment-sorting/SKILL.md) — Sort alignment files by coordinate or read name using samtools and pysam.
- [alignment-validation](alignment-files/alignment-validation/SKILL.md) — Validate alignment quality with insert size distribution, proper pairing rates, GC bias, strand balance, and other post-alignment metrics.
- [bam-statistics](alignment-files/bam-statistics/SKILL.md) — Generate alignment statistics using samtools flagstat, stats, depth, coverage, and mosdepth.
- [duplicate-handling](alignment-files/duplicate-handling/SKILL.md) — Mark and remove PCR/optical duplicates using samtools fixmate and markdup.
- [pileup-generation](alignment-files/pileup-generation/SKILL.md) — Generate pileup data for variant calling using samtools mpileup and pysam.
- [reference-operations](alignment-files/reference-operations/SKILL.md) — Generate consensus sequences and manage reference files using samtools.
- [sam-bam-basics](alignment-files/sam-bam-basics/SKILL.md) — View, convert, and understand SAM/BAM/CRAM alignment files using samtools and pysam.

## Alternative Splicing (9)
_RNA isoform and splicing pattern detection_

- [differential-splicing](alternative-splicing/differential-splicing/SKILL.md) — Detects differential alternative splicing between conditions using rMATS-turbo (binomial LRT on junction counts), leafcutter (Dirichlet-m…
- [isoform-switching](alternative-splicing/isoform-switching/SKILL.md) — Analyzes differential transcript usage (DTU) and isoform switches with functional consequence prediction (NMD via 50nt rule, ORF disrupti…
- [long-read-splicing](alternative-splicing/long-read-splicing/SKILL.md) — Analyzes alternative splicing from PacBio Iso-Seq (HiFi, Kinnex/MAS-Iso-seq) and Oxford Nanopore (direct cDNA, direct RNA, R10.4.1+) long…
- [outlier-splicing-detection](alternative-splicing/outlier-splicing-detection/SKILL.md) — Detects aberrant splicing in single rare-disease patients vs a control panel using FRASER 2.0 (Bioconductor; Beta-binomial autoencoder on…
- [sashimi-plots](alternative-splicing/sashimi-plots/SKILL.md) — Creates sashimi-style plots showing RNA-seq read coverage and splice junction counts using ggsashimi (general-purpose, condition-grouped …
- [single-cell-splicing](alternative-splicing/single-cell-splicing/SKILL.md) — Analyzes alternative splicing at single-cell resolution.
- [splice-variant-prediction](alternative-splicing/splice-variant-prediction/SKILL.md) — Predicts whether a DNA variant alters mRNA splicing using sequence-based deep-learning tools — SpliceAI (10kb context dilated CNN, clinic…
- [splicing-qc](alternative-splicing/splicing-qc/SKILL.md) — Assesses RNA-seq data quality specifically for alternative splicing analysis.
- [splicing-quantification](alternative-splicing/splicing-quantification/SKILL.md) — Quantifies alternative splicing as PSI (percent spliced in) from RNA-seq using rMATS-turbo (BAM-based event), SUPPA2 (TPM-based event), M…

## ATAC Seq (12)
_Chromatin accessibility peak calling and analysis_

- [atac-seq-allele-specific-accessibility](atac-seq/allele-specific-accessibility/SKILL.md) — Detect allele-specific chromatin accessibility from ATAC-seq using WASP, GATK ASEReadCounter, or RASQUAL.
- [atac-seq-atac-peak-calling](atac-seq/atac-peak-calling/SKILL.md) — Call accessible chromatin regions from ATAC-seq BAM files using MACS3, MACS2, Genrich, or HMMRATAC.
- [atac-seq-atac-qc](atac-seq/atac-qc/SKILL.md) — ATAC-seq library quality control -- TSS enrichment, FRiP, fragment-size periodicity, library complexity (NRF/PBC1/PBC2), mitochondrial fr…
- [atac-seq-co-accessibility](atac-seq/co-accessibility/SKILL.md) — Infer cis-regulatory connections (peak-to-peak co-accessibility) from scATAC-seq using Cicero, ArchR getCoAccessibility, or SCENIC+.
- [atac-seq-consensus-peakset](atac-seq/consensus-peakset/SKILL.md) — Build a differential-ready consensus peakset from per-replicate ATAC-seq peaks using iterative overlap removal, fixed-width re-centering,…
- [atac-seq-deep-learning-atac](atac-seq/deep-learning-atac/SKILL.md) — Sequence-based deep learning for ATAC-seq using chromBPNet, BPNet, scBasset, or EnFormer.
- [atac-seq-differential-accessibility](atac-seq/differential-accessibility/SKILL.md) — Identify differentially accessible chromatin regions across conditions using DiffBind, csaw, DESeq2, or edgeR.
- [atac-seq-enhancer-gene-linking](atac-seq/enhancer-gene-linking/SKILL.md) — Predict enhancer-gene regulatory connections from ATAC-seq using ABC, ENCODE-rE2G, HiChIP, or Cicero.
- [atac-seq-footprinting](atac-seq/footprinting/SKILL.md) — Detect transcription factor binding footprints in ATAC-seq using TOBIAS, HINT-ATAC, Wellington, or scprinter.
- [atac-seq-motif-deviation](atac-seq/motif-deviation/SKILL.md) — Analyze TF motif accessibility variability across samples or single cells using chromVAR.
- [atac-seq-nucleosome-positioning](atac-seq/nucleosome-positioning/SKILL.md) — Map nucleosome center positions, occupancy, and fuzziness from ATAC-seq fragment-size patterns using NucleoATAC, ATACseqQC, DANPOS3, or s…
- [atac-seq-single-cell-atac](atac-seq/single-cell-atac/SKILL.md) — Process and analyze single-cell ATAC-seq data with Signac, ArchR, SnapATAC2, or Cell Ranger ATAC.

## Causal Genomics (11)
_Mendelian randomization and genetic inference_

- [causal-genomics-colocalization-analysis](causal-genomics/colocalization-analysis/SKILL.md) — Test whether two or more traits share a causal variant at a locus using Bayesian colocalization (coloc.abf, coloc.susie, HyPrColoc, moloc…
- [causal-genomics-effector-gene-prioritization](causal-genomics/effector-gene-prioritization/SKILL.md) — Maps GWAS-implicated loci to candidate effector (causal) genes by integrating variant-to-gene (V2G) features via Open Targets L2G (Mountj…
- [causal-genomics-fine-mapping](causal-genomics/fine-mapping/SKILL.md) — Resolves GWAS associations to candidate causal variants and credible sets via SuSiE, susie_rss, FINEMAP, CAVIAR, DAP-G, PAINTOR, PolyFun,…
- [causal-genomics-genetic-correlation](causal-genomics/genetic-correlation/SKILL.md) — Estimate bivariate genetic correlation (rg) between traits from GWAS summary statistics or individual-level genotypes using cross-trait L…
- [causal-genomics-genomic-sem](causal-genomics/genomic-sem/SKILL.md) — Fits structural equation models to GWAS summary statistics using GenomicSEM (Grotzinger 2019), including common-factor models, confirmato…
- [causal-genomics-heritability-partitioning](causal-genomics/heritability-partitioning/SKILL.md) — Estimate SNP heritability and partition it across functional annotations, cell types, and loci from GWAS summary statistics or individual…
- [causal-genomics-mediation-analysis](causal-genomics/mediation-analysis/SKILL.md) — Decompose total effects into direct and indirect paths through mediators using mediation, CMAverse 4-way, HIMA/HIMA2 high-dimensional, BA…
- [causal-genomics-mendelian-randomization](causal-genomics/mendelian-randomization/SKILL.md) — Estimate causal effects of an exposure on an outcome from GWAS summary statistics using genetic instruments.
- [causal-genomics-pleiotropy-detection](causal-genomics/pleiotropy-detection/SKILL.md) — Detect and adjust for horizontal pleiotropy in two-sample Mendelian randomization by distinguishing uncorrelated (UHP) from correlated (C…
- [causal-genomics-proteome-mr-drug-target](causal-genomics/proteome-mr-drug-target/SKILL.md) — Runs cis-pQTL Mendelian randomization for drug-target validation using UKB-PPP (Olink), deCODE (SomaScan), Fenland, INTERVAL, ARIC, and F…
- [causal-genomics-transcriptome-wide-association](causal-genomics/transcriptome-wide-association/SKILL.md) — Performs gene-level association from GWAS summary statistics via genetically predicted tissue expression using FUSION, PrediXcan, S-Predi…

## Chemoinformatics (7)
_Molecular structure and drug discovery tools_

- [admet-prediction](chemoinformatics/admet-prediction/SKILL.md) — Predicts ADMET properties using ADMETlab 3.0 API or DeepChem models.
- [molecular-descriptors](chemoinformatics/molecular-descriptors/SKILL.md) — Calculates molecular descriptors and fingerprints using RDKit.
- [molecular-io](chemoinformatics/molecular-io/SKILL.md) — Reads, writes, and converts molecular file formats (SMILES, SDF, MOL2, PDB) using RDKit and Open Babel.
- [reaction-enumeration](chemoinformatics/reaction-enumeration/SKILL.md) — Enumerates chemical libraries through reaction SMARTS transformations using RDKit.
- [similarity-searching](chemoinformatics/similarity-searching/SKILL.md) — Performs molecular similarity searches using Tanimoto coefficient on fingerprints via RDKit.
- [substructure-search](chemoinformatics/substructure-search/SKILL.md) — Searches molecular libraries for substructure matches using SMARTS patterns with RDKit.
- [virtual-screening](chemoinformatics/virtual-screening/SKILL.md) — Performs structure-based virtual screening using AutoDock Vina 1.2 for molecular docking.

## ChIP Seq (7)
_Transcription factor binding site identification_

- [chipseq-qc](chip-seq/chipseq-qc/SKILL.md) — ChIP-seq quality control metrics including FRiP (Fraction of Reads in Peaks), cross-correlation analysis (NSC/RSC), library complexity, a…
- [chipseq-visualization](chip-seq/chipseq-visualization/SKILL.md) — Visualize ChIP-seq data using deepTools, Gviz, and ChIPseeker.
- [chipseq-differential-binding](chip-seq/differential-binding/SKILL.md) — Identifies differentially bound ChIP-seq regions between conditions using DiffBind (from BAMs), DESeq2, or PyDESeq2 (from count matrices).
- [chipseq-motif-analysis](chip-seq/motif-analysis/SKILL.md) — De novo motif discovery and known motif enrichment analysis using HOMER and MEME-ChIP.
- [chipseq-peak-annotation](chip-seq/peak-annotation/SKILL.md) — Annotate ChIP-seq peaks to genomic features and nearest genes.
- [chipseq-peak-calling](chip-seq/peak-calling/SKILL.md) — ChIP-seq peak calling using MACS3 and HOMER findPeaks.
- [chipseq-super-enhancers](chip-seq/super-enhancers/SKILL.md) — Identifies super-enhancers from H3K27ac ChIP-seq data using ROSE and related tools.

## Clinical Biostatistics (6)
_Statistical analysis for clinical trials_

- [clinical-biostatistics-categorical-tests](clinical-biostatistics/categorical-tests/SKILL.md) — Tests associations between categorical variables in clinical data using chi-square, Fisher's exact, and Cochran-Mantel-Haenszel tests.
- [clinical-biostatistics-cdisc-data](clinical-biostatistics/cdisc-data-handling/SKILL.md) — Reads and prepares CDISC SDTM clinical trial data for analysis.
- [clinical-biostatistics-effect-measures](clinical-biostatistics/effect-measures/SKILL.md) — Computes and interprets treatment effect measures including odds ratios, risk ratios, number needed to treat, and confidence intervals fr…
- [clinical-biostatistics-logistic-regression](clinical-biostatistics/logistic-regression/SKILL.md) — Performs logistic regression for clinical trial outcomes including binary, ordinal, and multinomial models.
- [clinical-biostatistics-subgroup-analysis](clinical-biostatistics/subgroup-analysis/SKILL.md) — Performs stratified and subgroup analyses for clinical trial data.
- [clinical-biostatistics-trial-reporting](clinical-biostatistics/trial-reporting/SKILL.md) — Prepares statistical tables and reports for clinical trials following regulatory standards.

## Clinical Databases (10)
_Variant and phenotype database queries_

- [clinical-databases-clinvar-lookup](clinical-databases/clinvar-lookup/SKILL.md) — Query ClinVar for variant pathogenicity classifications, review status, and disease associations via REST API or local VCF.
- [clinical-databases-dbsnp-queries](clinical-databases/dbsnp-queries/SKILL.md) — Query dbSNP for rsID lookups, variant annotations, and cross-references to other databases.
- [clinical-databases-gnomad-frequencies](clinical-databases/gnomad-frequencies/SKILL.md) — Query gnomAD for population allele frequencies to assess variant rarity.
- [clinical-databases-hla-typing](clinical-databases/hla-typing/SKILL.md) — Call HLA alleles from NGS data using OptiType, HLA-HD, or arcasHLA for immunogenomics applications.
- [clinical-databases-myvariant-queries](clinical-databases/myvariant-queries/SKILL.md) — Query myvariant.info API for aggregated variant annotations from multiple databases (ClinVar, gnomAD, dbSNP, COSMIC, etc.) in a single re…
- [clinical-databases-pharmacogenomics](clinical-databases/pharmacogenomics/SKILL.md) — Query PharmGKB and CPIC for drug-gene interactions, pharmacogenomic annotations, and dosing guidelines.
- [clinical-databases-polygenic-risk](clinical-databases/polygenic-risk/SKILL.md) — Calculate polygenic risk scores using PRSice-2, LDpred2, or PRS-CS from GWAS summary statistics.
- [clinical-databases-somatic-signatures](clinical-databases/somatic-signatures/SKILL.md) — Extract and analyze mutational signatures from somatic variants using SigProfiler or MutationalPatterns to characterize mutagenic processes.
- [clinical-databases-tumor-mutational-burden](clinical-databases/tumor-mutational-burden/SKILL.md) — Calculate tumor mutational burden from panel or WES data with proper normalization and clinical thresholds.
- [clinical-databases-variant-prioritization](clinical-databases/variant-prioritization/SKILL.md) — Filter and prioritize variants by pathogenicity, population frequency, and clinical evidence for rare disease analysis.

## CLIP Seq (5)
_Protein-RNA interaction mapping_

- [clip-seq-binding-site-annotation](clip-seq/binding-site-annotation/SKILL.md) — Annotate CLIP-seq binding sites to genomic features including 3'UTR, 5'UTR, CDS, introns, and ncRNAs.
- [clip-seq-clip-alignment](clip-seq/clip-alignment/SKILL.md) — Align CLIP-seq reads to the genome with crosslink site awareness.
- [clip-seq-clip-motif-analysis](clip-seq/clip-motif-analysis/SKILL.md) — Identify enriched sequence motifs at CLIP-seq binding sites for RBP binding specificity.
- [clip-seq-clip-peak-calling](clip-seq/clip-peak-calling/SKILL.md) — Call protein-RNA binding site peaks from CLIP-seq data using CLIPper, PureCLIP, or Piranha.
- [clip-seq-clip-preprocessing](clip-seq/clip-preprocessing/SKILL.md) — Preprocess CLIP-seq data including adapter trimming, UMI extraction, and PCR duplicate removal.

## Comparative Genomics (5)
_Cross-species sequence and synteny analysis_

- [comparative-genomics-ancestral-reconstruction](comparative-genomics/ancestral-reconstruction/SKILL.md) — Reconstruct ancestral sequences at phylogenetic nodes using PAML and IQ-TREE marginal likelihood methods.
- [comparative-genomics-hgt-detection](comparative-genomics/hgt-detection/SKILL.md) — Detect horizontal gene transfer events using HGTector, compositional analysis, and phylogenetic incongruence methods.
- [comparative-genomics-ortholog-inference](comparative-genomics/ortholog-inference/SKILL.md) — Infer orthologous gene groups across species using OrthoFinder and ProteinOrtho.
- [comparative-genomics-positive-selection](comparative-genomics/positive-selection/SKILL.md) — Detect positive selection using dN/dS (omega) tests with PAML codeml and HyPhy.
- [comparative-genomics-synteny-analysis](comparative-genomics/synteny-analysis/SKILL.md) — Analyze genome collinearity and syntenic blocks using MCScanX, SyRI, and JCVI for comparative genomics.

## Copy Number (4)
_Copy number variation detection and visualization_

- [copy-number-cnv-annotation](copy-number/cnv-annotation/SKILL.md) — Annotate CNVs with genes, pathways, and clinical significance.
- [copy-number-cnv-visualization](copy-number/cnv-visualization/SKILL.md) — Visualize copy number profiles, segments, and compare across samples.
- [copy-number-cnvkit-analysis](copy-number/cnvkit-analysis/SKILL.md) — Detect copy number variants from targeted/exome sequencing using CNVkit.
- [copy-number-gatk-cnv](copy-number/gatk-cnv/SKILL.md) — Call copy number variants using GATK best practices workflow.

## Crispr Screens (8)
_Pooled genetic screening analysis_

- [crispr-screens-base-editing-analysis](crispr-screens/base-editing-analysis/SKILL.md) — Analyzes base editing and prime editing outcomes including editing efficiency, bystander edits, and indel frequencies.
- [crispr-screens-batch-correction](crispr-screens/batch-correction/SKILL.md) — Batch effect correction for CRISPR screens.
- [crispr-screens-crispresso-editing](crispr-screens/crispresso-editing/SKILL.md) — CRISPResso2 for analyzing CRISPR gene editing outcomes.
- [crispr-screens-hit-calling](crispr-screens/hit-calling/SKILL.md) — Statistical methods for calling hits in CRISPR screens.
- [crispr-screens-jacks-analysis](crispr-screens/jacks-analysis/SKILL.md) — JACKS (Joint Analysis of CRISPR/Cas9 Knockout Screens) for modeling sgRNA efficacy and gene essentiality.
- [crispr-screens-library-design](crispr-screens/library-design/SKILL.md) — CRISPR library design for genetic screens.
- [crispr-screens-mageck-analysis](crispr-screens/mageck-analysis/SKILL.md) — MAGeCK (Model-based Analysis of Genome-wide CRISPR-Cas9 Knockout) for pooled CRISPR screen analysis.
- [crispr-screens-screen-qc](crispr-screens/screen-qc/SKILL.md) — Quality control for pooled CRISPR screens.

## Data Visualization (12)
_Publication-quality figure generation_

- [data-visualization-circos-plots](data-visualization/circos-plots/SKILL.md) — Create circular genome visualizations with Circos and pyCircos.
- [data-visualization-color-palettes](data-visualization/color-palettes/SKILL.md) — Select and apply colorblind-friendly palettes for scientific figures using viridis, RColorBrewer, and custom color schemes.
- [data-visualization-genome-browser-tracks](data-visualization/genome-browser-tracks/SKILL.md) — Generate genome browser visualizations using pyGenomeTracks or IGV batch scripting for publication figures.
- [data-visualization-genome-tracks](data-visualization/genome-tracks/SKILL.md) — Create genome browser-style visualizations showing multiple data tracks (coverage, peaks, genes) using pyGenomeTracks, Gviz, and IGV.
- [data-visualization-ggplot2-fundamentals](data-visualization/ggplot2-fundamentals/SKILL.md) — Create publication-quality scientific figures with ggplot2 including scatter plots, boxplots, heatmaps, and multi-panel layouts.
- [data-visualization-heatmaps-clustering](data-visualization/heatmaps-clustering/SKILL.md) — Create clustered heatmaps with row/column annotations using ComplexHeatmap, pheatmap, and seaborn for gene expression and omics data visu…
- [data-visualization-interactive-visualization](data-visualization/interactive-visualization/SKILL.md) — Create interactive HTML plots with plotly and bokeh for exploratory data analysis and web-based sharing of omics visualizations.
- [data-visualization-multipanel-figures](data-visualization/multipanel-figures/SKILL.md) — Combine multiple plots into publication-ready multi-panel figures using patchwork, cowplot, or matplotlib GridSpec with shared legends an…
- [data-visualization-network-visualization](data-visualization/network-visualization/SKILL.md) — Visualize biological networks including gene regulatory networks, protein interaction networks, and co-expression modules using NetworkX,…
- [data-visualization-specialized-omics-plots](data-visualization/specialized-omics-plots/SKILL.md) — Reusable plotting functions for common omics visualizations.
- [data-visualization-upset-plots](data-visualization/upset-plots/SKILL.md) — Create UpSet plots to visualize set intersections as an alternative to Venn diagrams using UpSetR or upsetplot.
- [data-visualization-volcano-customization](data-visualization/volcano-customization/SKILL.md) — Create publication-ready volcano plots with custom thresholds, gene labels, and highlighting using ggplot2, EnhancedVolcano, or matplotlib.

## Database Access (11)
_NCBI, UniProt, and biological database queries_

- [batch-downloads](database-access/batch-downloads/SKILL.md) — Download large datasets from NCBI efficiently using history server, batching, and rate limiting.
- [blast-searches](database-access/blast-searches/SKILL.md) — Run remote BLAST searches against NCBI databases using Biopython Bio.Blast.
- [entrez-fetch](database-access/entrez-fetch/SKILL.md) — Retrieve records from NCBI databases using Biopython Bio.Entrez.
- [entrez-link](database-access/entrez-link/SKILL.md) — Find cross-references between NCBI databases using Biopython Bio.Entrez.
- [entrez-search](database-access/entrez-search/SKILL.md) — Search NCBI databases using Biopython Bio.Entrez.
- [geo-data](database-access/geo-data/SKILL.md) — Query NCBI Gene Expression Omnibus (GEO) for expression datasets using Biopython Bio.Entrez.
- [interaction-databases](database-access/interaction-databases/SKILL.md) — Query protein-protein and gene interaction databases including STRING, BioGRID, and IntAct via their REST APIs and Python clients.
- [local-blast](database-access/local-blast/SKILL.md) — Run local BLAST searches using BLAST+ command-line tools.
- [sequence-similarity](database-access/sequence-similarity/SKILL.md) — Find homologous sequences using iterative BLAST (PSI-BLAST), profile HMMs (HMMER), and reciprocal best hit analysis.
- [sra-data](database-access/sra-data/SKILL.md) — Download sequencing data from NCBI SRA using the SRA toolkit.
- [uniprot-access](database-access/uniprot-access/SKILL.md) — Access UniProt protein database for sequences, annotations, and functional information.

## Differential Expression (6)
_RNA-seq statistical testing_

- [differential-expression-batch-correction](differential-expression/batch-correction/SKILL.md) — Remove batch effects from RNA-seq data using ComBat, ComBat-Seq, limma removeBatchEffect, and SVA for unknown batch variables.
- [de-results](differential-expression/de-results/SKILL.md) — Extract, filter, annotate, and export differential expression results from DESeq2 or edgeR.
- [de-visualization](differential-expression/de-visualization/SKILL.md) — Visualize differential expression results using DESeq2/edgeR built-in functions.
- [de-deseq2-basics](differential-expression/deseq2-basics/SKILL.md) — Perform differential expression analysis using DESeq2 in R/Bioconductor.
- [de-edger-basics](differential-expression/edger-basics/SKILL.md) — Perform differential expression analysis using edgeR in R/Bioconductor.
- [differential-expression-timeseries-de](differential-expression/timeseries-de/SKILL.md) — Analyze time-series RNA-seq data using limma voom with splines, maSigPro, and ImpulseDE2.

## Ecological Genomics (6)
_Environmental DNA and population analysis_

- [ecological-genomics-biodiversity-metrics](ecological-genomics/biodiversity-metrics/SKILL.md) — Calculates species richness, diversity, and turnover using the Hill number framework with iNEXT coverage-based rarefaction/extrapolation,…
- [ecological-genomics-community-ecology](ecological-genomics/community-ecology/SKILL.md) — Analyzes community composition using constrained ordination (CCA, RDA, db-RDA), variance partitioning (varpart), indicator species analys…
- [ecological-genomics-conservation-genetics](ecological-genomics/conservation-genetics/SKILL.md) — Assesses genetic health of populations for conservation using effective population size estimation (GONE2 for recent Ne trajectory, NeEst…
- [ecological-genomics-edna-metabarcoding](ecological-genomics/edna-metabarcoding/SKILL.md) — Processes environmental DNA metabarcoding data from raw amplicon reads to species occurrence tables using OBITools3, DADA2, and taxonomic…
- [ecological-genomics-landscape-genomics](ecological-genomics/landscape-genomics/SKILL.md) — Tests genotype-environment associations and identifies loci under local adaptation using LFMM2 (LEA), pcadapt outlier detection, OutFLANK…
- [ecological-genomics-species-delimitation](ecological-genomics/species-delimitation/SKILL.md) — Delimits species boundaries from molecular data using distance-based (ASAP), tree-based (bPTP, GMYC), and coalescent (BPP) methods.

## Epidemiological Genomics (5)
_Pathogen typing and outbreak investigation_

- [epidemiological-genomics-amr-surveillance](epidemiological-genomics/amr-surveillance/SKILL.md) — Detect and track antimicrobial resistance genes using AMRFinderPlus and ResFinder with epidemiological context.
- [epidemiological-genomics-pathogen-typing](epidemiological-genomics/pathogen-typing/SKILL.md) — Perform multi-locus sequence typing (MLST), core genome MLST, and SNP-based strain typing for bacterial isolate characterization using ml…
- [epidemiological-genomics-phylodynamics](epidemiological-genomics/phylodynamics/SKILL.md) — Construct time-scaled phylogenies and infer evolutionary dynamics using TreeTime and BEAST2 for outbreak analysis.
- [epidemiological-genomics-transmission-inference](epidemiological-genomics/transmission-inference/SKILL.md) — Infer pathogen transmission networks and identify likely transmission pairs using TransPhylo and outbreak reconstruction algorithms.
- [epidemiological-genomics-variant-surveillance](epidemiological-genomics/variant-surveillance/SKILL.md) — Assign pathogen lineages and track variants using Nextclade and pangolin for viral surveillance.

## Epitranscriptomics (5)
_RNA modification detection_

- [epitranscriptomics-m6a-differential](epitranscriptomics/m6a-differential/SKILL.md) — Identify differential m6A methylation between conditions from MeRIP-seq.
- [epitranscriptomics-m6a-peak-calling](epitranscriptomics/m6a-peak-calling/SKILL.md) — Call m6A peaks from MeRIP-seq IP vs input comparisons.
- [epitranscriptomics-m6anet-analysis](epitranscriptomics/m6anet-analysis/SKILL.md) — Detect m6A modifications from Oxford Nanopore direct RNA sequencing using m6Anet.
- [epitranscriptomics-merip-preprocessing](epitranscriptomics/merip-preprocessing/SKILL.md) — Align and QC MeRIP-seq IP and input samples for m6A analysis.
- [epitranscriptomics-modification-visualization](epitranscriptomics/modification-visualization/SKILL.md) — Create metagene plots and browser tracks for RNA modification data.

## Experimental Design (4)
_Power analysis and sample size calculation_

- [experimental-design-batch-design](experimental-design/batch-design/SKILL.md) — Designs experiments to minimize and account for batch effects using balanced layouts and blocking strategies.
- [experimental-design-multiple-testing](experimental-design/multiple-testing/SKILL.md) — Applies multiple testing correction methods including FDR, Bonferroni, and q-value for genomics data.
- [experimental-design-power-analysis](experimental-design/power-analysis/SKILL.md) — Calculates statistical power and minimum sample sizes for RNA-seq, ATAC-seq, and other sequencing experiments.
- [experimental-design-sample-size](experimental-design/sample-size/SKILL.md) — Estimates required sample sizes for differential expression, ChIP-seq, methylation, and proteomics studies.

## Expression Matrix (5)
_Count normalization and gene ID mapping_

- [expression-matrix-counts-ingest](expression-matrix/counts-ingest/SKILL.md) — Load gene expression count matrices from various formats including CSV, TSV, featureCounts, Salmon, kallisto, and 10X.
- [expression-matrix-gene-id-mapping](expression-matrix/gene-id-mapping/SKILL.md) — Convert between gene identifier systems including Ensembl, Entrez, HGNC symbols, and UniProt.
- [expression-matrix-metadata-joins](expression-matrix/metadata-joins/SKILL.md) — Merge sample metadata with count matrices and add gene annotations.
- [expression-matrix-normalization](expression-matrix/normalization/SKILL.md) — Normalize and transform RNA-seq count matrices for differential expression, visualization, and clustering.
- [expression-matrix-sparse-handling](expression-matrix/sparse-handling/SKILL.md) — Work with sparse matrices for memory-efficient storage of count data.

## Flow Cytometry (8)
_FCS file processing and cell population analysis_

- [flow-cytometry-bead-normalization](flow-cytometry/bead-normalization/SKILL.md) — Bead-based normalization for CyTOF and high-parameter flow cytometry.
- [flow-cytometry-clustering-phenotyping](flow-cytometry/clustering-phenotyping/SKILL.md) — Unsupervised clustering and cell type identification for flow/mass cytometry.
- [flow-cytometry-compensation-transformation](flow-cytometry/compensation-transformation/SKILL.md) — Spillover compensation and data transformation for flow cytometry.
- [flow-cytometry-cytometry-qc](flow-cytometry/cytometry-qc/SKILL.md) — Comprehensive quality control for flow cytometry and CyTOF data.
- [flow-cytometry-differential-analysis](flow-cytometry/differential-analysis/SKILL.md) — Differential abundance and state analysis for cytometry data.
- [flow-cytometry-doublet-detection](flow-cytometry/doublet-detection/SKILL.md) — Detect and remove doublets from flow and mass cytometry data.
- [flow-cytometry-fcs-handling](flow-cytometry/fcs-handling/SKILL.md) — Read and manipulate Flow Cytometry Standard (FCS) files.
- [flow-cytometry-gating-analysis](flow-cytometry/gating-analysis/SKILL.md) — Manual and automated gating for defining cell populations in flow cytometry.

## Gene Regulatory Networks (5)
_Transcription factor network inference_

- [gene-regulatory-networks-coexpression-networks](gene-regulatory-networks/coexpression-networks/SKILL.md) — Build weighted gene co-expression networks to identify modules of co-regulated genes and relate them to phenotypes using WGCNA and CEMiTool.
- [gene-regulatory-networks-differential-networks](gene-regulatory-networks/differential-networks/SKILL.md) — Compare gene regulatory and co-expression networks between biological conditions to identify rewired regulatory relationships using DiffC…
- [gene-regulatory-networks-multiomics-grn](gene-regulatory-networks/multiomics-grn/SKILL.md) — Build enhancer-driven gene regulatory networks by integrating single-cell RNA-seq and ATAC-seq data using SCENIC+ to identify eRegulons l…
- [gene-regulatory-networks-perturbation-simulation](gene-regulatory-networks/perturbation-simulation/SKILL.md) — Simulate transcription factor perturbation effects on cell state using CellOracle, which integrates GRN inference with in silico knockout…
- [gene-regulatory-networks-scenic-regulons](gene-regulatory-networks/scenic-regulons/SKILL.md) — Infer gene regulatory networks and identify transcription factor regulons from single-cell RNA-seq data using pySCENIC.

## Genome Annotation (6)
_Gene prediction and functional assignment_

- [genome-annotation-annotation-transfer](genome-annotation/annotation-transfer/SKILL.md) — Transfer gene annotations between genome assemblies using Liftoff for same-species annotation liftover and MiniProt for cross-species pro…
- [genome-annotation-eukaryotic-gene-prediction](genome-annotation/eukaryotic-gene-prediction/SKILL.md) — Predict protein-coding genes in eukaryotic genomes using BRAKER3 for combined RNA-seq and protein evidence, or GALBA for protein-only evi…
- [genome-annotation-functional-annotation](genome-annotation/functional-annotation/SKILL.md) — Assign GO terms, KEGG orthologs, Pfam domains, and EC numbers to predicted proteins using eggNOG-mapper and InterProScan.
- [genome-annotation-ncrna-annotation](genome-annotation/ncrna-annotation/SKILL.md) — Identify non-coding RNAs including tRNAs, rRNAs, snoRNAs, and regulatory RNAs using Infernal covariance model searches against Rfam and t…
- [genome-annotation-prokaryotic-annotation](genome-annotation/prokaryotic-annotation/SKILL.md) — Annotate bacterial and archaeal genomes with Bakta for comprehensive structural and functional annotation, or Prokka for lightweight anno…
- [genome-annotation-repeat-annotation](genome-annotation/repeat-annotation/SKILL.md) — Identify and classify repetitive elements and transposable elements using RepeatModeler for de novo repeat library construction and Repea…

## Genome Assembly (8)
_De novo genome assembly and quality assessment_

- [genome-assembly-assembly-polishing](genome-assembly/assembly-polishing/SKILL.md) — Polish genome assemblies to reduce errors using short reads (Pilon), long reads (Racon), or ONT-specific tools (medaka).
- [genome-assembly-assembly-qc](genome-assembly/assembly-qc/SKILL.md) — Assess genome assembly quality using QUAST for contiguity metrics and BUSCO for completeness.
- [genome-assembly-contamination-detection](genome-assembly/contamination-detection/SKILL.md) — Detect contamination and assess genome quality using CheckM, CheckM2, GTDB-Tk, and GUNC for metagenome-assembled genomes and isolate asse…
- [genome-assembly-hifi-assembly](genome-assembly/hifi-assembly/SKILL.md) — High-quality genome assembly from PacBio HiFi reads using hifiasm with phasing support.
- [genome-assembly-long-read-assembly](genome-assembly/long-read-assembly/SKILL.md) — De novo genome assembly from Oxford Nanopore or PacBio long reads using Flye and Canu.
- [genome-assembly-metagenome-assembly](genome-assembly/metagenome-assembly/SKILL.md) — Metagenome assembly from long reads using metaFlye and metaSPAdes with binning strategies.
- [genome-assembly-scaffolding](genome-assembly/scaffolding/SKILL.md) — Scaffold contigs into chromosome-level assemblies using Hi-C data with YaHS, 3D-DNA, SALSA2, and validate with BUSCO and contact maps.
- [genome-assembly-short-read-assembly](genome-assembly/short-read-assembly/SKILL.md) — De novo genome assembly from Illumina short reads using SPAdes.

## Genome Engineering (5)
_CRISPR guide design and off-target prediction_

- [genome-engineering-base-editing-design](genome-engineering/base-editing-design/SKILL.md) — Design guides for cytosine and adenine base editing using editing window optimization and BE-Hive outcome prediction.
- [genome-engineering-grna-design](genome-engineering/grna-design/SKILL.md) — Design guide RNAs for CRISPR-Cas9/Cas12a experiments using CRISPRscan and local scoring algorithms.
- [genome-engineering-hdr-template-design](genome-engineering/hdr-template-design/SKILL.md) — Design homology-directed repair donor templates for CRISPR knock-ins using primer3-py.
- [genome-engineering-off-target-prediction](genome-engineering/off-target-prediction/SKILL.md) — Predict CRISPR off-target sites using Cas-OFFinder and CFD scoring algorithms.
- [genome-engineering-prime-editing-design](genome-engineering/prime-editing-design/SKILL.md) — Design pegRNAs for prime editing using PrimeDesign algorithms.

## Genome Intervals (7)
_BED/GTF interval arithmetic operations_

- [genome-intervals-bed-file-basics](genome-intervals/bed-file-basics/SKILL.md) — BED file format fundamentals, creation, validation, and basic operations.
- [bedgraph-handling](genome-intervals/bedgraph-handling/SKILL.md) — Create, manipulate, and convert bedGraph files for genome browser visualization.
- [genome-intervals-bigwig-tracks](genome-intervals/bigwig-tracks/SKILL.md) — Create and read bigWig browser tracks for visualizing continuous genomic data.
- [genome-intervals-coverage-analysis](genome-intervals/coverage-analysis/SKILL.md) — Calculate read depth and coverage across genomic intervals using bedtools genomecov and coverage.
- [genome-intervals-gtf-gff-handling](genome-intervals/gtf-gff-handling/SKILL.md) — Parse, query, and convert GTF and GFF3 annotation files.
- [genome-intervals-interval-arithmetic](genome-intervals/interval-arithmetic/SKILL.md) — Core interval arithmetic operations including intersect, subtract, merge, complement, map, and groupby using bedtools and pybedtools.
- [genome-intervals-proximity-operations](genome-intervals/proximity-operations/SKILL.md) — Find nearest features, search within windows, and extend intervals using closest, window, flank, and slop operations.

## Hi-C Analysis (8)
_3D chromatin contact analysis_

- [hi-c-analysis-compartment-analysis](hi-c-analysis/compartment-analysis/SKILL.md) — Detect A/B compartments from Hi-C data using cooltools and eigenvector decomposition.
- [hi-c-analysis-contact-pairs](hi-c-analysis/contact-pairs/SKILL.md) — Process Hi-C read pairs using pairtools.
- [hi-c-analysis-hic-data-io](hi-c-analysis/hic-data-io/SKILL.md) — Load, convert, and manipulate Hi-C contact matrices using cooler format.
- [hi-c-analysis-hic-differential](hi-c-analysis/hic-differential/SKILL.md) — Compare Hi-C contact matrices between conditions to identify differential chromatin interactions.
- [hi-c-analysis-hic-visualization](hi-c-analysis/hic-visualization/SKILL.md) — Visualize Hi-C contact matrices, TADs, loops, and genomic features using matplotlib, cooltools, and HiCExplorer.
- [hi-c-analysis-loop-calling](hi-c-analysis/loop-calling/SKILL.md) — Detect chromatin loops and point interactions from Hi-C data using cooltools, chromosight, and HiCCUPS-like methods.
- [hi-c-analysis-matrix-operations](hi-c-analysis/matrix-operations/SKILL.md) — Balance, normalize, and transform Hi-C contact matrices using cooler and cooltools.
- [hi-c-analysis-tad-detection](hi-c-analysis/tad-detection/SKILL.md) — Call topologically associating domains (TADs) from Hi-C data using insulation score, HiCExplorer, and other methods.

## Imaging Mass Cytometry (6)
_Single-cell spatial proteomics_

- [imaging-mass-cytometry-cell-segmentation](imaging-mass-cytometry/cell-segmentation/SKILL.md) — Cell segmentation from multiplexed tissue images.
- [imaging-mass-cytometry-data-preprocessing](imaging-mass-cytometry/data-preprocessing/SKILL.md) — Load and preprocess imaging mass cytometry (IMC) and MIBI data.
- [imaging-mass-cytometry-interactive-annotation](imaging-mass-cytometry/interactive-annotation/SKILL.md) — Interactive cell type annotation for IMC data.
- [imaging-mass-cytometry-phenotyping](imaging-mass-cytometry/phenotyping/SKILL.md) — Cell type assignment from marker expression in IMC data.
- [imaging-mass-cytometry-quality-metrics](imaging-mass-cytometry/quality-metrics/SKILL.md) — Quality metrics for IMC data including signal-to-noise, channel correlation, tissue integrity, and acquisition QC.
- [imaging-mass-cytometry-spatial-analysis](imaging-mass-cytometry/spatial-analysis/SKILL.md) — Spatial analysis of cell neighborhoods and interactions in IMC data.

## Immunoinformatics (5)
_MHC binding and neoantigen prediction_

- [immunoinformatics-epitope-prediction](immunoinformatics/epitope-prediction/SKILL.md) — Predict B-cell and T-cell epitopes using BepiPred, IEDB tools, and structure-based methods for vaccine and antibody design.
- [immunoinformatics-immunogenicity-scoring](immunoinformatics/immunogenicity-scoring/SKILL.md) — Score and prioritize neoantigens and epitopes for immunogenicity using multi-factor models combining MHC binding, processing, expression,…
- [immunoinformatics-mhc-binding-prediction](immunoinformatics/mhc-binding-prediction/SKILL.md) — Predict peptide-MHC class I and II binding affinity using MHCflurry and NetMHCpan neural network models.
- [immunoinformatics-neoantigen-prediction](immunoinformatics/neoantigen-prediction/SKILL.md) — Identify tumor neoantigens from somatic mutations using pVACtools for personalized cancer immunotherapy.
- [immunoinformatics-tcr-epitope-binding](immunoinformatics/tcr-epitope-binding/SKILL.md) — Predict TCR-epitope specificity using ERGO-II and deep learning models for T-cell receptor antigen recognition.

## Liquid Biopsy (6)
_Cell-free DNA analysis and tumor fraction detection_

- [cfdna-preprocessing](liquid-biopsy/cfdna-preprocessing/SKILL.md) — Preprocesses cell-free DNA sequencing data including adapter trimming, alignment optimized for short fragments, and UMI-aware duplicate r…
- [ctdna-mutation-detection](liquid-biopsy/ctdna-mutation-detection/SKILL.md) — Detects somatic mutations in circulating tumor DNA using variant callers optimized for low allele fractions with UMI-based error suppress…
- [fragment-analysis](liquid-biopsy/fragment-analysis/SKILL.md) — Analyzes cfDNA fragment size distributions and fragmentomics features using FinaleToolkit or Griffin.
- [longitudinal-monitoring](liquid-biopsy/longitudinal-monitoring/SKILL.md) — Tracks ctDNA dynamics over time for treatment response monitoring using serial liquid biopsy samples.
- [methylation-based-detection](liquid-biopsy/methylation-based-detection/SKILL.md) — Analyzes cfDNA methylation patterns for cancer detection using cfMeDIP-seq or bisulfite sequencing with MethylDackel.
- [tumor-fraction-estimation](liquid-biopsy/tumor-fraction-estimation/SKILL.md) — Estimates circulating tumor DNA fraction from shallow whole-genome sequencing using ichorCNA.

## Long Read Sequencing (8)
_Nanopore and PacBio read processing_

- [basecalling](long-read-sequencing/basecalling/SKILL.md) — "Convert raw Nanopore signal data (FAST5/POD5) to nucleotide sequences using Dorado basecaller.
- [long-read-sequencing-clair3-variants](long-read-sequencing/clair3-variants/SKILL.md) — Deep learning-based variant calling from long reads using Clair3 for SNPs and small indels.
- [long-read-sequencing-isoseq-analysis](long-read-sequencing/isoseq-analysis/SKILL.md) — Analyze PacBio Iso-Seq data for full-length isoform discovery and quantification.
- [longread-alignment](long-read-sequencing/long-read-alignment/SKILL.md) — Align long reads using minimap2 for Oxford Nanopore and PacBio data.
- [longread-qc](long-read-sequencing/long-read-qc/SKILL.md) — Quality control for long-read sequencing data using NanoPlot, NanoStat, and chopper.
- [longread-medaka](long-read-sequencing/medaka-polishing/SKILL.md) — Polish assemblies and call variants from Oxford Nanopore data using medaka.
- [long-read-sequencing-nanopore-methylation](long-read-sequencing/nanopore-methylation/SKILL.md) — Calls DNA methylation from Oxford Nanopore sequencing data using signal-level analysis.
- [longread-structural-variants](long-read-sequencing/structural-variants/SKILL.md) — Detect structural variants from long-read alignments using Sniffles, cuteSV, and SVIM.

## Machine Learning (6)
_Biomarker discovery and model validation_

- [machine-learning-atlas-mapping](machine-learning/atlas-mapping/SKILL.md) — Maps query single-cell data to reference atlases using scArches transfer learning with scVI and scANVI models.
- [machine-learning-biomarker-discovery](machine-learning/biomarker-discovery/SKILL.md) — Selects informative features for biomarker discovery using Boruta all-relevant selection, mRMR minimum redundancy, and LASSO regularization.
- [machine-learning-model-validation](machine-learning/model-validation/SKILL.md) — Implements nested cross-validation and stratified splits for unbiased model evaluation on biomedical datasets.
- [machine-learning-omics-classifiers](machine-learning/omics-classifiers/SKILL.md) — Builds classification models for omics data using RandomForest, XGBoost, and logistic regression with sklearn-compatible APIs.
- [machine-learning-prediction-explanation](machine-learning/prediction-explanation/SKILL.md) — Explains machine learning predictions on omics data using SHAP values and LIME for feature attribution.
- [machine-learning-survival-analysis](machine-learning/survival-analysis/SKILL.md) — Analyzes time-to-event data using Kaplan-Meier curves, log-rank tests, and Cox proportional hazards regression with lifelines.

## Metabolomics (8)
_Mass spectrometry metabolite identification_

- [metabolomics-lipidomics](metabolomics/lipidomics/SKILL.md) — Specialized lipidomics analysis for lipid identification, quantification, and pathway interpretation.
- [metabolomics-metabolite-annotation](metabolomics/metabolite-annotation/SKILL.md) — Metabolite identification from m/z and retention time.
- [metabolomics-msdial-preprocessing](metabolomics/msdial-preprocessing/SKILL.md) — MS-DIAL-based metabolomics preprocessing as alternative to XCMS.
- [metabolomics-normalization-qc](metabolomics/normalization-qc/SKILL.md) — Quality control and normalization for metabolomics data.
- [metabolomics-pathway-mapping](metabolomics/pathway-mapping/SKILL.md) — Map metabolites to biological pathways using KEGG, Reactome, and MetaboAnalyst.
- [metabolomics-statistical-analysis](metabolomics/statistical-analysis/SKILL.md) — Statistical analysis for metabolomics data.
- [metabolomics-targeted-analysis](metabolomics/targeted-analysis/SKILL.md) — Targeted metabolomics analysis using MRM/SRM with standard curves.
- [metabolomics-xcms-preprocessing](metabolomics/xcms-preprocessing/SKILL.md) — XCMS3 workflow for LC-MS/MS metabolomics preprocessing.

## Metagenomics (7)
_Microbial community composition analysis_

- [metagenomics-abundance](metagenomics/abundance-estimation/SKILL.md) — Species abundance estimation using Bracken with Kraken2 output.
- [metagenomics-amr-detection](metagenomics/amr-detection/SKILL.md) — Detect antimicrobial resistance genes using AMRFinderPlus, ResFinder, and CARD.
- [metagenomics-functional-profiling](metagenomics/functional-profiling/SKILL.md) — Profile functional potential of metagenomes using HUMAnN3 and similar tools.
- [metagenomics-kraken](metagenomics/kraken-classification/SKILL.md) — Taxonomic classification of metagenomic reads using Kraken2.
- [metagenomics-visualization](metagenomics/metagenome-visualization/SKILL.md) — Visualize metagenomic profiles using R (phyloseq, microbiome) and Python (matplotlib, seaborn).
- [metagenomics-metaphlan](metagenomics/metaphlan-profiling/SKILL.md) — Marker gene-based taxonomic profiling using MetaPhlAn 4.
- [metagenomics-strain-tracking](metagenomics/strain-tracking/SKILL.md) — Track bacterial strains using MASH, sourmash, fastANI, and inStrain.

## Methylation Analysis (5)
_DNA methylation and bisulfite alignment_

- [methylation-bismark-alignment](methylation-analysis/bismark-alignment/SKILL.md) — Bisulfite sequencing read alignment using Bismark with bowtie2/hisat2.
- [methylation-differential-cpg](methylation-analysis/differential-cpg-testing/SKILL.md) — Per-CpG differential methylation testing from bisulfite sequencing count data or beta-value matrices.
- [methylation-dmr-detection](methylation-analysis/dmr-detection/SKILL.md) — Differentially methylated region (DMR) detection using methylKit tiles, bsseq BSmooth, and DMRcate.
- [methylation-calling](methylation-analysis/methylation-calling/SKILL.md) — Extract methylation calls from Bismark BAM files using bismark_methylation_extractor.
- [methylation-methylkit](methylation-analysis/methylkit-analysis/SKILL.md) — DNA methylation analysis with methylKit in R.

## Microbiome (6)
_16S amplicon and microbiota profiling_

- [microbiome-amplicon-processing](microbiome/amplicon-processing/SKILL.md) — Amplicon sequence variant (ASV) inference from 16S rRNA or ITS amplicon sequencing using DADA2.
- [microbiome-differential-abundance](microbiome/differential-abundance/SKILL.md) — Differential abundance testing for microbiome data using compositionally-aware methods like ALDEx2, ANCOM-BC2, and MaAsLin2.
- [microbiome-diversity-analysis](microbiome/diversity-analysis/SKILL.md) — Alpha and beta diversity analysis for microbiome data.
- [microbiome-functional-prediction](microbiome/functional-prediction/SKILL.md) — Predict metagenome functional content from 16S rRNA marker gene data using PICRUSt2.
- [microbiome-qiime2-workflow](microbiome/qiime2-workflow/SKILL.md) — QIIME2 command-line workflow for 16S/ITS amplicon analysis.
- [microbiome-taxonomy-assignment](microbiome/taxonomy-assignment/SKILL.md) — Taxonomic classification of ASVs using reference databases like SILVA, GTDB, or UNITE.

## Multi Omics Integration (4)
_Cross-modality data fusion_

- [multi-omics-data-harmonization](multi-omics-integration/data-harmonization/SKILL.md) — Preprocessing and harmonization of multi-omics data before integration.
- [multi-omics-mixomics-analysis](multi-omics-integration/mixomics-analysis/SKILL.md) — Supervised and unsupervised multi-omics integration with mixOmics.
- [multi-omics-mofa-integration](multi-omics-integration/mofa-integration/SKILL.md) — Multi-Omics Factor Analysis (MOFA2) for unsupervised integration of multiple data modalities.
- [multi-omics-similarity-network](multi-omics-integration/similarity-network/SKILL.md) — Similarity Network Fusion (SNF) for patient stratification using multi-omics data.

## Pathway Analysis (6)
_GO/KEGG enrichment testing_

- [pathway-enrichment-visualization](pathway-analysis/enrichment-visualization/SKILL.md) — Visualize enrichment results using enrichplot package functions.
- [pathway-go-enrichment](pathway-analysis/go-enrichment/SKILL.md) — Gene Ontology over-representation analysis using clusterProfiler enrichGO.
- [pathway-gsea](pathway-analysis/gsea/SKILL.md) — Gene Set Enrichment Analysis using clusterProfiler gseGO and gseKEGG.
- [pathway-kegg-pathways](pathway-analysis/kegg-pathways/SKILL.md) — KEGG pathway and module enrichment analysis using clusterProfiler enrichKEGG and enrichMKEGG.
- [pathway-reactome](pathway-analysis/reactome-pathways/SKILL.md) — Reactome pathway enrichment using ReactomePA package.
- [pathway-wikipathways](pathway-analysis/wikipathways/SKILL.md) — WikiPathways enrichment using clusterProfiler and rWikiPathways.

## Phasing Imputation (4)
_Haplotype phasing and genotype inference_

- [phasing-imputation-genotype-imputation](phasing-imputation/genotype-imputation/SKILL.md) — Impute missing genotypes using reference panels with Beagle or Minimac4.
- [phasing-imputation-haplotype-phasing](phasing-imputation/haplotype-phasing/SKILL.md) — Phase genotypes into haplotypes using Beagle or SHAPEIT.
- [phasing-imputation-imputation-qc](phasing-imputation/imputation-qc/SKILL.md) — Quality control of phasing and imputation results.
- [phasing-imputation-reference-panels](phasing-imputation/reference-panels/SKILL.md) — Download, prepare, and manage reference panels for phasing and imputation.

## Phylogenetics (8)
_Evolutionary tree construction and analysis_

- [phylo-bayesian-inference](phylogenetics/bayesian-inference/SKILL.md) — Run Bayesian phylogenetic analysis with MrBayes, BEAST2, RevBayes, and PhyloBayes including MCMC convergence diagnostics and model compar…
- [phylo-distance-calculations](phylogenetics/distance-calculations/SKILL.md) — Compute evolutionary distances and build phylogenetic trees using Biopython Bio.Phylo.TreeConstruction.
- [phylo-divergence-dating](phylogenetics/divergence-dating/SKILL.md) — Estimate divergence times using molecular clock models with BEAST2, MCMCTree, and TreePL.
- [phylo-modern-tree-inference](phylogenetics/modern-tree-inference/SKILL.md) — Build maximum likelihood phylogenetic trees using IQ-TREE2 and RAxML-NG with expert model selection, branch support assessment, and topol…
- [phylo-species-trees](phylogenetics/species-trees/SKILL.md) — Estimate species trees using coalescent methods including ASTRAL-III, wASTRAL, ASTRAL-Pro, SVDQuartets, and BPP.
- [phylo-tree-io](phylogenetics/tree-io/SKILL.md) — Read, write, and convert phylogenetic tree files using Biopython Bio.Phylo.
- [phylo-tree-manipulation](phylogenetics/tree-manipulation/SKILL.md) — Modify phylogenetic tree structure using Biopython Bio.Phylo.
- [phylo-tree-visualization](phylogenetics/tree-visualization/SKILL.md) — Draw and export phylogenetic trees using Biopython Bio.Phylo with matplotlib and modern alternatives.

## Population Genetics (6)
_GWAS and population structure analysis_

- [population-genetics-association-testing](population-genetics/association-testing/SKILL.md) — Genome-wide association studies (GWAS) with PLINK.
- [population-genetics-linkage-disequilibrium](population-genetics/linkage-disequilibrium/SKILL.md) — Calculate linkage disequilibrium statistics (r², D'), perform LD pruning for population structure analysis, identify haplotype blocks, an…
- [population-genetics-plink-basics](population-genetics/plink-basics/SKILL.md) — PLINK file formats, format conversion, and quality control filtering for population genetics.
- [population-genetics-population-structure](population-genetics/population-structure/SKILL.md) — Analyze population structure using PCA and admixture analysis with PLINK and ADMIXTURE.
- [population-genetics-scikit-allel-analysis](population-genetics/scikit-allel-analysis/SKILL.md) — Python population genetics with scikit-allel.
- [population-genetics-selection-statistics](population-genetics/selection-statistics/SKILL.md) — Detect signatures of natural selection using Fst, Tajima's D, iHS, XP-EHH, and other selection statistics.

## Primer Design (3)
_PCR and qPCR primer generation_

- [primer-design-primer-basics](primer-design/primer-basics/SKILL.md) — Design PCR primers for a target sequence using primer3-py.
- [primer-design-primer-validation](primer-design/primer-validation/SKILL.md) — Validate PCR primers for specificity, dimers, hairpins, and secondary structures using primer3-py thermodynamic calculations.
- [primer-design-qpcr-primers](primer-design/qpcr-primers/SKILL.md) — Design qPCR primers and TaqMan/molecular beacon probes using primer3-py.

## Proteomics (9)
_Mass spec quantification and protein abundance_

- [proteomics-data-import](proteomics/data-import/SKILL.md) — Load and parse mass spectrometry data formats including mzML, mzXML, and quantification tool outputs like MaxQuant proteinGroups.txt.
- [proteomics-dia-analysis](proteomics/dia-analysis/SKILL.md) — Data-independent acquisition (DIA) proteomics analysis with DIA-NN and other tools.
- [proteomics-differential-abundance](proteomics/differential-abundance/SKILL.md) — Statistical testing for differentially abundant proteins between conditions.
- [proteomics-peptide-identification](proteomics/peptide-identification/SKILL.md) — Peptide-spectrum matching and protein identification from MS/MS data.
- [proteomics-protein-inference](proteomics/protein-inference/SKILL.md) — Protein grouping and inference from peptide identifications.
- [proteomics-proteomics-qc](proteomics/proteomics-qc/SKILL.md) — Quality control and assessment for proteomics data.
- [proteomics-ptm-analysis](proteomics/ptm-analysis/SKILL.md) — Post-translational modification analysis including phosphorylation, acetylation, and ubiquitination.
- [proteomics-quantification](proteomics/quantification/SKILL.md) — Protein quantification from mass spectrometry data including label-free (LFQ, intensity-based), isobaric labeling (TMT, iTRAQ), and metab…
- [proteomics-spectral-libraries](proteomics/spectral-libraries/SKILL.md) — Build, manage, and search spectral libraries for proteomics.

## Read Alignment (4)
_Short-read mapping to reference genomes_

- [read-alignment-bowtie2-alignment](read-alignment/bowtie2-alignment/SKILL.md) — Align short reads using Bowtie2 with local or end-to-end modes.
- [read-alignment-bwa-alignment](read-alignment/bwa-alignment/SKILL.md) — Align DNA short reads to reference genomes using bwa-mem2, the faster successor to BWA-MEM.
- [read-alignment-hisat2-alignment](read-alignment/hisat2-alignment/SKILL.md) — Align RNA-seq reads with HISAT2, a memory-efficient splice-aware aligner.
- [read-alignment-star-alignment](read-alignment/star-alignment/SKILL.md) — Align RNA-seq reads with STAR (Spliced Transcripts Alignment to a Reference).

## Read Qc (7)
_Sequencing quality assessment and trimming_

- [read-qc-adapter-trimming](read-qc/adapter-trimming/SKILL.md) — Remove sequencing adapters from FASTQ files using Cutadapt and Trimmomatic.
- [read-qc-contamination-screening](read-qc/contamination-screening/SKILL.md) — Detect sample contamination and cross-species reads using FastQ Screen.
- [read-qc-fastp-workflow](read-qc/fastp-workflow/SKILL.md) — All-in-one read preprocessing with fastp including adapter trimming, quality filtering, deduplication, base correction, and HTML report g…
- [read-qc-quality-filtering](read-qc/quality-filtering/SKILL.md) — Filter reads by quality scores, length, and N content using Trimmomatic and fastp.
- [read-qc-quality-reports](read-qc/quality-reports/SKILL.md) — Generate and interpret quality reports from FASTQ files using FastQC and MultiQC.
- [rnaseq-qc](read-qc/rnaseq-qc/SKILL.md) — RNA-seq specific quality control including rRNA contamination detection, strandedness verification, gene body coverage, and transcript in…
- [read-qc-umi-processing](read-qc/umi-processing/SKILL.md) — Extract, process, and deduplicate reads using Unique Molecular Identifiers (UMIs) with umi_tools.

## Reporting (5)
_Reproducible report generation_

- [reporting-automated-qc-reports](reporting/automated-qc-reports/SKILL.md) — Generates standardized quality control reports by aggregating metrics from FastQC, alignment, and other tools using MultiQC.
- [reporting-figure-export](reporting/figure-export/SKILL.md) — Exports publication-ready figures in various formats with proper resolution, sizing, and typography.
- [reporting-jupyter-reports](reporting/jupyter-reports/SKILL.md) — Creates reproducible Jupyter notebooks for bioinformatics analysis with parameterization using papermill.
- [reporting-quarto-reports](reporting/quarto-reports/SKILL.md) — Build reproducible scientific documents, presentations, and websites with Quarto supporting R, Python, Julia, and Observable JS.
- [reporting-rmarkdown-reports](reporting/rmarkdown-reports/SKILL.md) — Create reproducible bioinformatics analysis reports with R Markdown including code, results, and visualizations in HTML, PDF, or Word for…

## Restriction Analysis (4)
_Enzyme site mapping and digestion prediction_

- [restriction-enzyme-selection](restriction-analysis/enzyme-selection/SKILL.md) — Select restriction enzymes by criteria using Biopython Bio.Restriction.
- [restriction-fragment-analysis](restriction-analysis/fragment-analysis/SKILL.md) — Analyze restriction digest fragments using Biopython Bio.Restriction.
- [restriction-mapping](restriction-analysis/restriction-mapping/SKILL.md) — Create restriction maps showing enzyme cut positions on DNA sequences using Biopython Bio.Restriction.
- [restriction-sites](restriction-analysis/restriction-sites/SKILL.md) — Find restriction enzyme cut sites in DNA sequences using Biopython Bio.Restriction.

## Ribo Seq (5)
_Ribosome profiling and translation efficiency_

- [ribo-seq-orf-detection](ribo-seq/orf-detection/SKILL.md) — Detect and quantify translated ORFs from Ribo-seq data including uORFs and novel ORFs using RiboCode and ORFquant.
- [ribo-seq-riboseq-preprocessing](ribo-seq/riboseq-preprocessing/SKILL.md) — Preprocess ribosome profiling data including adapter trimming, size selection, rRNA removal, and alignment.
- [ribo-seq-ribosome-periodicity](ribo-seq/ribosome-periodicity/SKILL.md) — Validate Ribo-seq data quality by checking 3-nucleotide periodicity and calculating P-site offsets.
- [ribo-seq-ribosome-stalling](ribo-seq/ribosome-stalling/SKILL.md) — Detect ribosome pausing and stalling sites from Ribo-seq data at codon resolution.
- [ribo-seq-translation-efficiency](ribo-seq/translation-efficiency/SKILL.md) — Calculate translation efficiency (TE) as the ratio of ribosome occupancy to mRNA abundance.

## RNA Quantification (4)
_Gene and transcript abundance estimation_

- [rna-quantification-alignment-free-quant](rna-quantification/alignment-free-quant/SKILL.md) — Quantify transcript expression using pseudo-alignment with Salmon or kallisto.
- [rna-quantification-count-matrix-qc](rna-quantification/count-matrix-qc/SKILL.md) — Quality control and exploration of RNA-seq count matrices before differential expression.
- [rna-quantification-featurecounts-counting](rna-quantification/featurecounts-counting/SKILL.md) — Count reads per gene from aligned BAM files using Subread featureCounts.
- [rna-quantification-tximport-workflow](rna-quantification/tximport-workflow/SKILL.md) — Import transcript-level quantifications from Salmon/kallisto into R for gene-level analysis with DESeq2/edgeR using tximport or tximeta.

## RNA Structure (3)
_Secondary structure prediction_

- [rna-structure-ncrna-search](rna-structure/ncrna-search/SKILL.md) — Searches for non-coding RNA homologs and classifies RNA families using Infernal covariance model searches against the Rfam database.
- [rna-structure-secondary-structure-prediction](rna-structure/secondary-structure-prediction/SKILL.md) — Predicts RNA secondary structures using minimum free energy folding and partition function analysis with ViennaRNA (RNAfold, RNAalifold, …
- [rna-structure-structure-probing](rna-structure/structure-probing/SKILL.md) — Analyzes experimental RNA structure probing data from SHAPE-MaP and DMS-MaPseq experiments using ShapeMapper2.

## Sequence Io (9)
_FASTA/FASTQ format conversion and parsing_

- [batch-processing](sequence-io/batch-processing/SKILL.md) — Process multiple sequence files in batch using Biopython.
- [compressed-files](sequence-io/compressed-files/SKILL.md) — Read and write compressed sequence files (gzip, bzip2, BGZF) using Biopython.
- [fastq-quality](sequence-io/fastq-quality/SKILL.md) — Work with FASTQ quality scores using Biopython.
- [filter-sequences](sequence-io/filter-sequences/SKILL.md) — Filter and select sequences by criteria (length, ID, GC content, patterns) using Biopython.
- [format-conversion](sequence-io/format-conversion/SKILL.md) — Convert between sequence file formats (FASTA, FASTQ, GenBank, EMBL) using Biopython Bio.SeqIO.
- [paired-end-fastq](sequence-io/paired-end-fastq/SKILL.md) — Handle paired-end FASTQ files (R1/R2) using Biopython.
- [read-sequences](sequence-io/read-sequences/SKILL.md) — Read biological sequence files (FASTA, FASTQ, GenBank, EMBL, ABI, SFF) using Biopython Bio.SeqIO.
- [sequence-statistics](sequence-io/sequence-statistics/SKILL.md) — Calculate sequence statistics (N50, length distribution, GC content, summary reports) using Biopython.
- [write-sequences](sequence-io/write-sequences/SKILL.md) — Write biological sequences to files (FASTA, FASTQ, GenBank, EMBL) using Biopython Bio.SeqIO.

## Sequence Manipulation (7)
_Transcription, translation, and motif search_

- [codon-usage](sequence-manipulation/codon-usage/SKILL.md) — Analyze codon usage, calculate CAI (Codon Adaptation Index), and examine synonymous codon bias using Biopython.
- [motif-search](sequence-manipulation/motif-search/SKILL.md) — Find patterns, motifs, and subsequences in biological sequences using Biopython.
- [reverse-complement](sequence-manipulation/reverse-complement/SKILL.md) — Generate reverse complements and complements of DNA/RNA sequences using Biopython.
- [seq-objects](sequence-manipulation/seq-objects/SKILL.md) — Create and manipulate Seq, MutableSeq, and SeqRecord objects using Biopython.
- [sequence-properties](sequence-manipulation/sequence-properties/SKILL.md) — Calculate sequence properties like GC content, molecular weight, isoelectric point, and GC skew using Biopython.
- [sequence-slicing](sequence-manipulation/sequence-slicing/SKILL.md) — Slice, extract, and concatenate biological sequences using Biopython.
- [transcription-translation](sequence-manipulation/transcription-translation/SKILL.md) — Transcribe DNA to RNA and translate to protein using Biopython.

## Single Cell (14)
_scRNA-seq clustering and cell type annotation_

- [single-cell-batch-integration](single-cell/batch-integration/SKILL.md) — Integrate multiple scRNA-seq samples/batches using Harmony, scVI, Seurat anchors, and fastMNN.
- [single-cell-cell-annotation](single-cell/cell-annotation/SKILL.md) — Automated cell type annotation using reference-based methods including CellTypist, scPred, SingleR, and Azimuth for consistent, reproduci…
- [single-cell-cell-communication](single-cell/cell-communication/SKILL.md) — Infer cell-cell communication networks from scRNA-seq data using CellChat, NicheNet, and LIANA for ligand-receptor interaction analysis.
- [single-cell-clustering](single-cell/clustering/SKILL.md) — Dimensionality reduction and clustering for single-cell RNA-seq using Seurat (R) and Scanpy (Python).
- [single-cell-data-io](single-cell/data-io/SKILL.md) — Read, write, and create single-cell data objects using Seurat (R) and Scanpy (Python).
- [single-cell-doublet-detection](single-cell/doublet-detection/SKILL.md) — Detect and remove doublets (multiple cells captured in one droplet) from single-cell RNA-seq data.
- [single-cell-lineage-tracing](single-cell/lineage-tracing/SKILL.md) — Reconstruct cell lineage trees from CRISPR barcode tracing or mitochondrial mutations.
- [single-cell-markers-annotation](single-cell/markers-annotation/SKILL.md) — Find marker genes and annotate cell types in single-cell RNA-seq using Seurat (R) and Scanpy (Python).
- [single-cell-metabolite-communication](single-cell/metabolite-communication/SKILL.md) — Analyze metabolite-mediated cell-cell communication using MeboCost for metabolic signaling inference between cell types.
- [single-cell-multimodal-integration](single-cell/multimodal-integration/SKILL.md) — Analyze multi-modal single-cell data (CITE-seq, Multiome, spatial).
- [single-cell-perturb-seq](single-cell/perturb-seq/SKILL.md) — Analyze Perturb-seq and CROP-seq CRISPR screening data integrated with scRNA-seq.
- [single-cell-preprocessing](single-cell/preprocessing/SKILL.md) — Quality control, filtering, and normalization for single-cell RNA-seq using Seurat (R) and Scanpy (Python).
- [single-cell-scatac-analysis](single-cell/scatac-analysis/SKILL.md) — Single-cell ATAC-seq analysis with Signac (R/Seurat) and ArchR.
- [single-cell-trajectory-inference](single-cell/trajectory-inference/SKILL.md) — Infer developmental trajectories and pseudotime from single-cell RNA-seq data using Monocle3, Slingshot, and scVelo for RNA velocity anal…

## Small RNA Seq (5)
_miRNA and piRNA analysis_

- [small-rna-seq-differential-mirna](small-rna-seq/differential-mirna/SKILL.md) — Perform differential expression analysis of miRNAs between conditions using DESeq2 or edgeR with small RNA-specific considerations.
- [small-rna-seq-mirdeep2-analysis](small-rna-seq/mirdeep2-analysis/SKILL.md) — Discover novel miRNAs and quantify known miRNAs using miRDeep2 de novo prediction from small RNA-seq data.
- [small-rna-seq-mirge3-analysis](small-rna-seq/mirge3-analysis/SKILL.md) — Fast miRNA quantification with isomiR detection and A-to-I editing analysis using miRge3.
- [small-rna-seq-smrna-preprocessing](small-rna-seq/smrna-preprocessing/SKILL.md) — Preprocess small RNA sequencing data with adapter trimming and size selection optimized for miRNA, piRNA, and other small RNAs.
- [small-rna-seq-target-prediction](small-rna-seq/target-prediction/SKILL.md) — Predict miRNA target genes using sequence-based algorithms and database lookups.

## Spatial Transcriptomics (11)
_Tissue imaging and location-based expression_

- [spatial-transcriptomics-image-analysis](spatial-transcriptomics/image-analysis/SKILL.md) — Process and analyze tissue images from spatial transcriptomics data using Squidpy.
- [spatial-transcriptomics-spatial-communication](spatial-transcriptomics/spatial-communication/SKILL.md) — Analyze cell-cell communication in spatial transcriptomics data using ligand-receptor analysis with Squidpy.
- [spatial-transcriptomics-spatial-data-io](spatial-transcriptomics/spatial-data-io/SKILL.md) — Load spatial transcriptomics data from Visium, Xenium, MERFISH, Slide-seq, and other platforms using Squidpy and SpatialData.
- [spatial-transcriptomics-spatial-deconvolution](spatial-transcriptomics/spatial-deconvolution/SKILL.md) — Estimate cell type composition in spatial transcriptomics spots using reference-based deconvolution.
- [spatial-transcriptomics-spatial-domains](spatial-transcriptomics/spatial-domains/SKILL.md) — Identify spatial domains and tissue regions in spatial transcriptomics data using Squidpy and Scanpy.
- [spatial-transcriptomics-spatial-multiomics](spatial-transcriptomics/spatial-multiomics/SKILL.md) — Analyze high-resolution spatial platforms like Slide-seq, Stereo-seq, and Visium HD.
- [spatial-transcriptomics-spatial-neighbors](spatial-transcriptomics/spatial-neighbors/SKILL.md) — Build spatial neighbor graphs for spatial transcriptomics data using Squidpy.
- [spatial-transcriptomics-spatial-preprocessing](spatial-transcriptomics/spatial-preprocessing/SKILL.md) — Quality control, filtering, normalization, and feature selection for spatial transcriptomics data.
- [spatial-transcriptomics-spatial-proteomics](spatial-transcriptomics/spatial-proteomics/SKILL.md) — Analyzes spatial proteomics data from CODEX, IMC, and MIBI platforms including cell segmentation and protein colocalization.
- [spatial-transcriptomics-spatial-statistics](spatial-transcriptomics/spatial-statistics/SKILL.md) — Compute spatial statistics for spatial transcriptomics data using Squidpy.
- [spatial-transcriptomics-spatial-visualization](spatial-transcriptomics/spatial-visualization/SKILL.md) — Visualize spatial transcriptomics data using Squidpy and Scanpy.

## Structural Biology (6)
_PDB parsing and protein structure prediction_

- [structural-biology-alphafold-predictions](structural-biology/alphafold-predictions/SKILL.md) — Access and analyze AlphaFold protein structure predictions.
- [pdb-geometric-analysis](structural-biology/geometric-analysis/SKILL.md) — Perform geometric calculations on protein structures using Biopython Bio.PDB.
- [structural-biology-modern-structure-prediction](structural-biology/modern-structure-prediction/SKILL.md) — Predict protein structures using modern ML models including AlphaFold3, ESMFold, Chai-1, and Boltz-1.
- [pdb-structure-io](structural-biology/structure-io/SKILL.md) — Parse and write protein structure files using Biopython Bio.PDB.
- [pdb-structure-modification](structural-biology/structure-modification/SKILL.md) — Modify protein structures using Biopython Bio.PDB.
- [pdb-structure-navigation](structural-biology/structure-navigation/SKILL.md) — Navigate protein structure hierarchy using Biopython Bio.PDB SMCRA model.

## Systems Biology (5)
_Metabolic modeling and flux analysis_

- [systems-biology-context-specific-models](systems-biology/context-specific-models/SKILL.md) — Build tissue and condition-specific metabolic models using GIMME, iMAT, and INIT algorithms with expression data constraints.
- [systems-biology-flux-balance-analysis](systems-biology/flux-balance-analysis/SKILL.md) — Perform flux balance analysis (FBA) and flux variability analysis (FVA) on genome-scale metabolic models using COBRApy.
- [systems-biology-gene-essentiality](systems-biology/gene-essentiality/SKILL.md) — Perform in silico gene knockout analysis and synthetic lethality screens using COBRApy single and double deletions.
- [systems-biology-metabolic-reconstruction](systems-biology/metabolic-reconstruction/SKILL.md) — Build genome-scale metabolic models from genome sequences using CarveMe and gapseq for automated reconstruction.
- [systems-biology-model-curation](systems-biology/model-curation/SKILL.md) — Validate, gap-fill, and curate genome-scale metabolic models using memote for quality scores and COBRApy for manual curation.

## TCR/BCR Analysis (5)
_Immune receptor repertoire analysis_

- [tcr-bcr-analysis-immcantation-analysis](tcr-bcr-analysis/immcantation-analysis/SKILL.md) — Analyze BCR repertoires for somatic hypermutation, clonal lineages, and B cell phylogenetics using the Immcantation framework.
- [tcr-bcr-analysis-mixcr-analysis](tcr-bcr-analysis/mixcr-analysis/SKILL.md) — Perform V(D)J alignment and clonotype assembly from TCR-seq or BCR-seq data using MiXCR.
- [tcr-bcr-analysis-repertoire-visualization](tcr-bcr-analysis/repertoire-visualization/SKILL.md) — Create publication-quality visualizations of immune repertoire data including circos plots, clone tracking, diversity plots, and network …
- [tcr-bcr-analysis-scirpy-analysis](tcr-bcr-analysis/scirpy-analysis/SKILL.md) — Analyze single-cell TCR and BCR data integrated with gene expression using scirpy.
- [tcr-bcr-analysis-vdjtools-analysis](tcr-bcr-analysis/vdjtools-analysis/SKILL.md) — Calculate immune repertoire diversity metrics, compare samples, and track clonal dynamics using VDJtools.

## Temporal Genomics (5)
_Time-series and circadian expression analysis_

- [temporal-genomics-circadian-rhythms](temporal-genomics/circadian-rhythms/SKILL.md) — Detects circadian and ultradian rhythms in time-series omics data using CosinorPy cosinor models, MetaCycle (JTK_CYCLE, ARSER), and RAIN …
- [temporal-genomics-periodicity-detection](temporal-genomics/periodicity-detection/SKILL.md) — Discovers periodic signals of unknown period in time-series omics data using Lomb-Scargle periodograms (scipy), autocorrelation, and wave…
- [temporal-genomics-temporal-clustering](temporal-genomics/temporal-clustering/SKILL.md) — Clusters genes by temporal expression profile shape using Mfuzz soft clustering, TCseq, and DEGreport degPatterns.
- [temporal-genomics-temporal-grn](temporal-genomics/temporal-grn/SKILL.md) — Infers dynamic gene regulatory networks from bulk time-series expression data using Granger causality (statsmodels), dynGENIE3 (Extra-Tre…
- [temporal-genomics-trajectory-modeling](temporal-genomics/trajectory-modeling/SKILL.md) — Models continuous temporal trajectories from bulk or time-resolved omics data using generalized additive models (mgcv), spline regression…

## Variant Calling (13)
_SNP, indel, and structural variant detection_

- [variant-calling-clinical-interpretation](variant-calling/clinical-interpretation/SKILL.md) — Clinical variant interpretation using ClinVar, ACMG guidelines, and pathogenicity predictors.
- [consensus-sequences](variant-calling/consensus-sequences/SKILL.md) — Generate consensus FASTA sequences by applying VCF variants to a reference using bcftools consensus.
- [variant-calling-deepvariant](variant-calling/deepvariant/SKILL.md) — Deep learning-based variant calling with Google DeepVariant.
- [variant-calling-filtering-best-practices](variant-calling/filtering-best-practices/SKILL.md) — Comprehensive variant filtering including GATK VQSR, hard filters, bcftools expressions, and quality metric interpretation for SNPs and i…
- [gatk-variant-calling](variant-calling/gatk-variant-calling/SKILL.md) — Variant calling with GATK HaplotypeCaller following best practices.
- [variant-calling-joint-calling](variant-calling/joint-calling/SKILL.md) — Joint genotype calling across multiple samples using GATK CombineGVCFs and GenotypeGVCFs.
- [variant-calling-structural-variant-calling](variant-calling/structural-variant-calling/SKILL.md) — Call structural variants (SVs) from sequencing data using Manta, Delly, GRIDSS, and LUMPY.
- [variant-annotation](variant-calling/variant-annotation/SKILL.md) — Comprehensive variant annotation using bcftools annotate/csq, VEP, SnpEff, and ANNOVAR.
- [variant-calling](variant-calling/variant-calling/SKILL.md) — Call SNPs and indels from aligned reads using bcftools mpileup and call.
- [variant-normalization](variant-calling/variant-normalization/SKILL.md) — Normalize indel representation, decompose MNPs, and split multiallelic variants using bcftools norm.
- [vcf-basics](variant-calling/vcf-basics/SKILL.md) — View, query, and understand VCF/BCF variant files using bcftools and cyvcf2.
- [vcf-manipulation](variant-calling/vcf-manipulation/SKILL.md) — Merge, concatenate, sort, intersect, and subset VCF files using bcftools.
- [vcf-statistics](variant-calling/vcf-statistics/SKILL.md) — Generate variant statistics, sample concordance, and quality metrics using bcftools stats and gtcheck.

## Workflow Management (4)
_Snakemake and Nextflow pipeline frameworks_

- [workflow-management-cwl-workflows](workflow-management/cwl-workflows/SKILL.md) — Create portable, standards-based bioinformatics pipelines with Common Workflow Language (CWL).
- [workflow-management-nextflow-pipelines](workflow-management/nextflow-pipelines/SKILL.md) — Create scalable, containerized bioinformatics pipelines with Nextflow DSL2 supporting Docker, Singularity, and cloud execution.
- [workflow-management-snakemake-workflows](workflow-management/snakemake-workflows/SKILL.md) — Build reproducible bioinformatics pipelines with Snakemake using rules, wildcards, and automatic dependency resolution.
- [workflow-management-wdl-workflows](workflow-management/wdl-workflows/SKILL.md) — Create portable bioinformatics pipelines with Workflow Description Language (WDL) using Cromwell or miniwdl execution engines.

## Workflows (41)
_End-to-end analysis pipelines_

- [workflows-atacseq-pipeline](workflows/atacseq-pipeline/SKILL.md) — End-to-end ATAC-seq workflow from FASTQ files to differential accessibility and TF footprinting.
- [workflows-biomarker-pipeline](workflows/biomarker-pipeline/SKILL.md) — End-to-end biomarker discovery workflow from expression data to validated biomarker panels.
- [workflows-causal-genomics-pipeline](workflows/causal-genomics-pipeline/SKILL.md) — End-to-end post-GWAS causal inference pipeline orchestrating heritability partitioning, genetic correlation, Mendelian randomization with…
- [workflows-chipseq-pipeline](workflows/chipseq-pipeline/SKILL.md) — End-to-end ChIP-seq workflow from FASTQ files to annotated peaks.
- [workflows-clinical-trial-pipeline](workflows/clinical-trial-pipeline/SKILL.md) — End-to-end clinical trial analysis workflow from CDISC data loading through statistical testing to regulatory-compliant reporting.
- [workflows-clip-pipeline](workflows/clip-pipeline/SKILL.md) — End-to-end CLIP-seq analysis from FASTQ to binding sites and motif enrichment.
- [workflows-cnv-pipeline](workflows/cnv-pipeline/SKILL.md) — End-to-end copy number variant detection workflow from BAM files.
- [workflows-crispr-editing-pipeline](workflows/crispr-editing-pipeline/SKILL.md) — End-to-end CRISPR experiment design from target selection to delivery-ready constructs.
- [workflows-crispr-screen-pipeline](workflows/crispr-screen-pipeline/SKILL.md) — End-to-end CRISPR screen analysis from FASTQ to hit genes.
- [workflows-cytometry-pipeline](workflows/cytometry-pipeline/SKILL.md) — End-to-end flow cytometry workflow from FCS files to differential analysis.
- [workflows-edna-pipeline](workflows/edna-pipeline/SKILL.md) — End-to-end eDNA metabarcoding from raw amplicons to community ecology.
- [workflows-expression-to-pathways](workflows/expression-to-pathways/SKILL.md) — Workflow from differential expression results to functional enrichment analysis.
- [workflows-fastq-to-variants](workflows/fastq-to-variants/SKILL.md) — End-to-end DNA sequencing workflow from FASTQ files to variant calls.
- [workflows-genome-annotation-pipeline](workflows/genome-annotation-pipeline/SKILL.md) — End-to-end genome annotation pipeline from assembled contigs to functional annotation, covering repeat masking, gene prediction, and func…
- [workflows-genome-assembly-pipeline](workflows/genome-assembly-pipeline/SKILL.md) — End-to-end genome assembly workflow from reads to polished assembly with QC.
- [workflows-grn-pipeline](workflows/grn-pipeline/SKILL.md) — End-to-end gene regulatory network inference pipeline from processed single-cell data to regulon discovery and perturbation simulation.
- [workflows-gwas-pipeline](workflows/gwas-pipeline/SKILL.md) — End-to-end GWAS workflow from VCF to association results.
- [workflows-hic-pipeline](workflows/hic-pipeline/SKILL.md) — End-to-end Hi-C analysis workflow from contact pairs to compartments, TADs, and loops.
- [workflows-imc-pipeline](workflows/imc-pipeline/SKILL.md) — End-to-end imaging mass cytometry workflow from raw acquisitions to spatial cell analysis.
- [liquid-biopsy-pipeline](workflows/liquid-biopsy-pipeline/SKILL.md) — Cell-free DNA analysis pipeline from plasma sequencing to tumor monitoring.
- [workflows-longread-sv-pipeline](workflows/longread-sv-pipeline/SKILL.md) — End-to-end workflow for detecting structural variants from long-read sequencing data.
- [workflows-merip-pipeline](workflows/merip-pipeline/SKILL.md) — End-to-end MeRIP-seq analysis from FASTQ to m6A peaks and differential methylation.
- [workflows-metabolic-modeling-pipeline](workflows/metabolic-modeling-pipeline/SKILL.md) — End-to-end genome-scale metabolic modeling from genome sequence to flux predictions.
- [workflows-metabolomics-pipeline](workflows/metabolomics-pipeline/SKILL.md) — End-to-end metabolomics workflow from raw MS data to pathway analysis.
- [workflows-metagenomics-pipeline](workflows/metagenomics-pipeline/SKILL.md) — End-to-end metagenomics workflow from FASTQ to taxonomic and functional profiles.
- [workflows-methylation-pipeline](workflows/methylation-pipeline/SKILL.md) — End-to-end bisulfite sequencing workflow from FASTQ to differentially methylated regions.
- [workflows-microbiome-pipeline](workflows/microbiome-pipeline/SKILL.md) — End-to-end 16S amplicon workflow from FASTQ reads to differential abundance.
- [workflows-multi-omics-pipeline](workflows/multi-omics-pipeline/SKILL.md) — End-to-end multi-omics integration workflow.
- [workflows-multiome-pipeline](workflows/multiome-pipeline/SKILL.md) — End-to-end multiome workflow for joint scRNA-seq + scATAC-seq analysis.
- [workflows-neoantigen-pipeline](workflows/neoantigen-pipeline/SKILL.md) — End-to-end neoantigen discovery from somatic variants to ranked vaccine candidates.
- [workflows-outbreak-pipeline](workflows/outbreak-pipeline/SKILL.md) — End-to-end outbreak investigation from pathogen isolates to transmission networks.
- [workflows-proteomics-pipeline](workflows/proteomics-pipeline/SKILL.md) — End-to-end proteomics workflow from MaxQuant output to differential protein abundance.
- [workflows-riboseq-pipeline](workflows/riboseq-pipeline/SKILL.md) — End-to-end Ribo-seq analysis from FASTQ to translation efficiency and ORF detection.
- [workflows-rnaseq-to-de](workflows/rnaseq-to-de/SKILL.md) — End-to-end RNA-seq workflow from FASTQ files to differential expression results.
- [workflows-scrnaseq-pipeline](workflows/scrnaseq-pipeline/SKILL.md) — End-to-end single-cell RNA-seq workflow from 10X Genomics data to annotated cell types.
- [workflows-smrna-pipeline](workflows/smrna-pipeline/SKILL.md) — End-to-end small RNA-seq analysis from FASTQ to differential miRNA expression.
- [workflows-somatic-variant-pipeline](workflows/somatic-variant-pipeline/SKILL.md) — End-to-end somatic variant calling from tumor-normal paired samples using Mutect2 or Strelka2.
- [workflows-spatial-pipeline](workflows/spatial-pipeline/SKILL.md) — End-to-end spatial transcriptomics workflow for Visium/Xenium data.
- [splicing-pipeline](workflows/splicing-pipeline/SKILL.md) — End-to-end alternative splicing analysis from FASTQ to differential splicing results for short-read bulk RNA-seq.
- [workflows-tcr-pipeline](workflows/tcr-pipeline/SKILL.md) — End-to-end TCR/BCR repertoire analysis from FASTQ to clonotype diversity metrics.
- [workflows-timecourse-pipeline](workflows/timecourse-pipeline/SKILL.md) — End-to-end time-course analysis from expression matrix to temporal patterns and enrichment.
