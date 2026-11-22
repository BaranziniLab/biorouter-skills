# Running and reviewing nf-core pipelines

> Merged from the former `nextflow-nfcore` component (Biorouter original, bundle version 1.0.0) into `nf-core-pipelines` at 1.1.0. Nothing was dropped; the text below is the former component as written.

# Nextflow and nf-core Workflow Management

Use this skill when the user asks to run a pipeline, convert an ad hoc analysis into a workflow, or review Nextflow/nf-core execution.

## Preflight

- Confirm Nextflow version and Java runtime.
- Choose executor/profile: local, Docker, Apptainer/Singularity, conda, SLURM, AWS Batch, or Seqera Platform.
- Validate input samplesheet and reference genome assets.
- Set `-profile` explicitly.
- Define output directory and work directory.
- Estimate resources before launch.

## nf-core Rules

- Start from the pipeline's official schema and samplesheet template.
- Run `nextflow run <pipeline> -profile test,<container-profile>` before real data.
- Pin pipeline version with `-r`.
- Use `-resume` only when inputs and parameters are intentionally unchanged.
- Save `params.json`, timeline, report, trace, and DAG.

## Review Checklist

- No absolute paths in portable configs unless site-specific.
- Containers are pinned.
- Sample IDs are stable and unique.
- MultiQC report exists and is inspected.
- Failed processes are debugged from `.command.err`, `.command.out`, and `.command.sh`.

## Related Skills

- `bio-skills/workflows/*`
- `ucsf-hpc`
- `replication-package-audit`


## Usage guide (former `usage-guide.md`)

# Nextflow and nf-core Usage Guide

Example prompts:

- "Set up nf-core/rnaseq for these FASTQ files on SLURM."
- "Review this Nextflow config for portability and reproducibility."
- "Explain why this process failed from `.command.err` and the trace file."

The agent will pin versions, run test profiles first, and preserve execution reports.
