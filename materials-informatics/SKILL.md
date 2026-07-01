---
name: materials-informatics
description: Guide computational materials and molecular-structure workflows with pymatgen, ASE-style structures, crystals, compositions, phase diagrams, descriptors, and provenance for materials datasets.
user-invocable: true
license: Apache-2.0
---

# Materials Informatics

Source adaptation: BioRouter-original synthesis inspired by broad Scientific Agent Skills and Auto-Empirical Research Skills capability patterns, rewritten under Apache-2.0. Do not copy upstream text; use this as a native BioRouter routing and quality-control checklist.

## When to Use

Use this skill when the user asks for Materials. Load more specific BioSkills, BRXT extensions, or language skills when the task touches a concrete dataset, file format, package, or platform.

## Intake

Collect the minimum context before acting:

- Research question or operational goal.
- Data source, file format, platform, package, or API involved.
- Unit of analysis and expected output.
- Privacy, credential, licensing, and compute constraints.
- Whether the user wants a plan, executable code, review, or installed-tool workflow.

## Native BioRouter Routing

Prefer these BioRouter-native routes before writing new glue code:

- Use relevant BRXT extensions when platform/API access is needed.
- Use `scientific-research` for broad research orchestration.
- Use `citation-temporal-integrity` and `claim-evidence-integrity` for evidence-heavy deliverables.
- Use `replication-package-audit` when outputs must be reproducible.
- Use `python-scripting`, `r-scripting`, or BioSkills for package-specific code style.

## Quality Gates

Before presenting results as final:

1. State the data provenance and tool/package versions.
2. Separate exploratory output from confirmatory evidence.
3. Check that identifiers, coordinates, sample ids, citations, or run ids are preserved.
4. Identify assumptions that could change the conclusion.
5. Provide a rerunnable command, notebook cell, or workflow outline when execution is involved.
6. Mark anything requiring credentials, proprietary data, or external services as unverified unless it was actually checked.

## Output Pattern

Return a compact work plan first, then the implementation or review. For each result, include:

- Decision made.
- Evidence or file/API source.
- Failure modes.
- Next verification step.
