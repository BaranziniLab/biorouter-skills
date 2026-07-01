---
name: structural-biology-protein-language-models
description: Use protein language models such as ESM-style embeddings for sequence representation, variant effect scoring, remote homology, structure-aware annotation, and downstream ML features. Use when a protein sequence task benefits from learned embeddings rather than only alignment or motif rules.
tool_type: python
primary_tool: esm
user-invocable: false
license: Apache-2.0
---

# Protein Language Models

Use this skill for protein sequence representation and variant prioritization with ESM-style embeddings or compatible models.

## Gate Checks

- Sequence alphabet and length are supported by the chosen model.
- Isoform, species, and residue numbering are documented.
- Embedding use is justified relative to alignment-based alternatives.
- Variant scoring is calibrated against known controls when possible.
- GPU/CPU resource needs are checked before running large models.

## Workflow

1. Validate FASTA inputs and remove ambiguous records if needed.
2. Select model size based on task and compute budget.
3. Generate per-sequence or per-residue embeddings.
4. Use embeddings for clustering, annotation, variant effect ranking, or downstream ML.
5. Save model name, checkpoint, tokenization, and pooling method.

## Reporting Rules

- Do not present embeddings as mechanistic proof.
- Report whether scores are zero-shot, fine-tuned, or downstream supervised predictions.
- Keep residue numbering traceable to the input sequence.

## Related Skills

- `structural-biology/protein-structure-prediction`
- `sequence-io`
- `comparative-genomics/ortholog-inference`
