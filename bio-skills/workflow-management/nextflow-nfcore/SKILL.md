---
name: workflow-management-nextflow-nfcore
description: Design, run, and review Nextflow/nf-core biomedical workflows with profile selection, container strategy, channel inputs, resume behavior, resource configuration, Tower/Seqera notes, and reproducibility checks. Use when a sequencing or omics task should be executed as a portable pipeline rather than ad hoc scripts.
tool_type: workflow
primary_tool: nextflow
user-invocable: false
license: Apache-2.0
---

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
