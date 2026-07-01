---
name: hugging-science-resource-discovery
description: Find and evaluate Hugging Face scientific models, datasets, Spaces, and papers with license, provenance, benchmark, and fit checks. Use when users ask for scientific ML resources, model cards, datasets, embeddings, checkpoints, or reproducible AI assets from Hugging Face.
user-invocable: true
license: Apache-2.0
---

# Hugging Science Resource Discovery

Source adaptation: BioRouter-original synthesis inspired by Scientific Agent Skills Hugging Face discovery patterns, rewritten under Apache-2.0.

## When to Use

Use this skill for scientific resource discovery on Hugging Face: models, datasets, Spaces, collections, papers, adapters, embeddings, or benchmark artifacts. Prefer `scientific-machine-learning` for model-building plans and this skill for resource selection.

## Intake

Collect:

- Domain and task: biomedical, chemistry, materials, geospatial, clinical, text, imaging, time series, or other.
- Required modality, input/output schema, and benchmark target.
- License and redistribution constraints.
- Runtime constraints: CPU/GPU, memory, latency, offline use.
- Privacy requirements and whether data can leave the local machine.

## Search and Triage

For each candidate resource, capture:

- Stable repo id and URL.
- Resource type: model, dataset, Space, paper, collection, or adapter.
- License, model card/data card completeness, and citation.
- Training/evaluation data provenance.
- Supported tasks and modalities.
- Last update date and maintainer signals.
- Known risks: restricted use, missing license, weak benchmarks, leakage, or unsafe clinical claims.

## BioRouter Routes

- Use `scientific-machine-learning` for training/evaluation plans.
- Use `drug-discovery-benchmarks`, `materials-informatics`, `geospatial-science`, or `biomedical-imaging-pathology` for domain-specific evaluation.
- Use `citation-temporal-integrity` when model cards cite papers.
- Use `replication-package-audit` before trusting published benchmark code.

## Selection Gates

Recommend a resource only when:

1. The license permits the intended use.
2. The model or dataset card explains provenance.
3. The benchmark matches the user's task.
4. Leakage and contamination risks are considered.
5. Hardware and dependency requirements are feasible.
6. Clinical or regulated use is framed as research support unless validated separately.

## Output Shape

Return a ranked table with: resource, URL, license, fit, evidence, risks, and next verification command.
