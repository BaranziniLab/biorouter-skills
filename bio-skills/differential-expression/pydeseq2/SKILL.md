---
name: differential-expression-pydeseq2
description: Run DESeq2-style bulk RNA-seq differential expression in Python with PyDESeq2, including count matrix validation, design formula checks, size-factor estimation, dispersion fitting, Wald/LRT contrasts, shrinkage guidance, and exportable result tables. Use when the project is Python-first or needs DESeq2-compatible methods without switching to R.
tool_type: python
primary_tool: pydeseq2
user-invocable: false
license: Apache-2.0
---

## Version Compatibility

Reference examples target: pydeseq2 0.4+, anndata 0.10+, pandas 2.1+, numpy 1.26+.

Before running examples, verify installed signatures with `python -c "import pydeseq2, inspect; print(pydeseq2.__version__)"`. PyDESeq2 has changed constructor names across releases; adapt to the installed API rather than retrying stale code.

# PyDESeq2 Differential Expression

Use PyDESeq2 for bulk RNA-seq count data when the user wants a Python-native DESeq2-style workflow. For established Bioconductor pipelines, prefer `differential-expression/deseq2-basics`.

## Gate Checks

- Counts are raw integer gene counts, not TPM/FPKM/CPM/log-normalized values.
- Sample metadata rows match count-matrix columns exactly.
- The design formula encodes the biological question and known batches.
- Replicates exist for each level of the tested factor.
- Contrasts are named before looking at volcano plots.

## Workflow

1. Load counts and sample metadata.
2. Drop genes with negligible counts.
3. Create a `DeseqDataSet` with explicit design factors.
4. Fit size factors and dispersions.
5. Run Wald or LRT statistics.
6. Extract a named contrast with log2 fold-change, SE, p-value, and adjusted p-value.
7. Export full and filtered tables.
8. Produce QC plots: size factors, dispersion trend, PCA, MA plot, volcano plot.

## Reporting Rules

- State the reference level and contrast direction.
- Use adjusted p-values for discovery claims.
- Interpret shrunken log2 fold changes for ranking, not as a replacement for the statistical test unless the method supports that use.
- Do not combine PyDESeq2 and normalized-count tests in the same claim.

## Related Skills

- `differential-expression/deseq2-basics`
- `differential-expression/de-results`
- `differential-expression/de-visualization`
- `experimental-design/multiple-testing`
