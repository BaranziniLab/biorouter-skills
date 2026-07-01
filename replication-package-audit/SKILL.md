---
name: replication-package-audit
description: "Audit a research project for reproducibility: master script, relative paths, environment capture, seeds, data provenance, restricted data notes, figure/table mapping, logs, and clean-run evidence. Use before declaring an analysis, manuscript, or package ready to share or submit."
user-invocable: true
license: Apache-2.0
---

# Replication Package Audit

Source adaptation: BioRouter-original synthesis from Auto-Empirical Research Skills AER replication/open-science workflows and BioRouter release verification patterns, rewritten under Apache-2.0.

Use this skill when a user asks to prepare, inspect, or submit a reproducible research bundle.

## Required Package Contents

- `README` with data access, software requirements, run order, expected runtime, and output map.
- Clean entry point such as `run_all.sh`, `run_all.R`, `Snakefile`, `main.nf`, or `Makefile`.
- Relative paths only; no user-specific absolute paths.
- Raw/intermediate/final data separation, with restricted data instructions when needed.
- Script-to-output map for every table, figure, and appendix exhibit.
- Environment capture: package lockfile, `sessionInfo()`, `renv.lock`, `requirements.txt`, `uv.lock`, `environment.yml`, container, or exact module list.
- Random seeds for stochastic steps.
- Logs or clean-run transcript.
- License and data-use notes.

## Audit Steps

1. Build a file manifest and identify the intended entry point.
2. Check for absolute paths, machine-specific home directories, and hidden dependencies.
3. Verify every reported exhibit can be traced to a script.
4. Confirm raw data provenance and restricted-data handling.
5. Run or dry-run the entry point when safe.
6. Compare generated output names to manuscript references.
7. Record missing software, runtime failures, and unverifiable steps.

## Pass Criteria

A package passes only if a new analyst can reproduce the public outputs from documented inputs without private knowledge. If data cannot be shared, the package must still include synthetic/sample data or a documented restricted-data workflow.

## Output Format

Return a compact audit:

| Check | Status | Evidence | Fix |
|---|---|---|---|

End with `Ready`, `Ready with restrictions`, or `Not ready`.
