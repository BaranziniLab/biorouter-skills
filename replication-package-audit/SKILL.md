---
name: replication-package-audit
description: "Audit a research package and its paper for reproducibility and publication readiness: clean-run entry point, relative paths, environment capture, seeds, logs, table and figure mapping, paper-to-code consistency, data and code availability statements, and an item-by-item reporting-guideline check (CONSORT, STROBE, PRISMA, TRIPOD+AI, STARD, SPIRIT, ARRIVE). Use when a user asks to prepare, inspect or submit a reproducible research bundle, check open-science readiness, or check a manuscript against a reporting checklist."
user-invocable: true
license: Apache-2.0 AND MIT AND BSD-3-Clause AND CC-BY-4.0 AND CC0-1.0
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "Aperivue/medsci-skills/skills/check-reporting@7e9d133dd0216c29b0e030729e3719c3db5e0973; uw-ssec/savvy/plugins/ai-research-workflows/skills/ensuring-reproducibility@e1084bba4ef18cfe9ce16a459e69df1ebe5018b0; claesbackman/AI-research-feedback/Skills/review-paper-code@949d82792ea20c30806147539ed2c70a8898260a"
---

# Replication Package Audit

Source adaptation: Biorouter-original audit (ideas from Auto-Empirical Research Skills replication workflows, no text copied), plus material adapted from Aperivue/medsci-skills `check-reporting` (MIT), uw-ssec/savvy `ensuring-reproducibility` (BSD-3-Clause) and claesbackman/AI-research-feedback `review-paper-code` (MIT). The bundled reporting checklists reproduce guideline text published under CC BY 4.0 (CC0 for ARRIVE 2.0). Licences and changes are in `LICENSE-UPSTREAM`.

Use this skill when a user asks to prepare, inspect or submit a reproducible research bundle, or to check that a paper is ready to publish beyond its statistics. It ends in one verdict: `Ready`, `Ready with restrictions` or `Not ready`.

This skill replaces `open-science-review`. If that skill is also installed, it is an earlier version of the disclosure and checklist part of this one and should yield to it.

Set `SKILL_DIR` to the skill directory Biorouter lists when this skill loads. Run scripts through the Developer shell; they are standard-library Python 3.

## 1. Required package contents

- `README` with data access, software requirements, run order, expected runtime and output map.
- Clean entry point such as `run_all.sh`, `run_all.R`, `Snakefile`, `main.nf`, `_targets.R` or `Makefile`.
- Relative paths only; no user-specific absolute paths.
- Raw, intermediate and final data separated, with restricted-data instructions when needed.
- Script-to-output map for every table, figure and appendix exhibit.
- Environment capture: lockfile (`renv.lock`, `uv.lock`, `pixi.lock`, `environment.yml`), `sessionInfo()`, a container, or an exact module list.
- Random seeds for stochastic steps.
- Logs or a clean-run transcript.
- Licence and data-use notes.

## 2. Audit steps

1. Build a file manifest and identify the intended entry point.
2. Check for absolute paths, machine-specific home directories and hidden dependencies.
3. Verify every reported exhibit can be traced to a script.
4. Confirm raw data provenance and restricted-data handling.
5. Run or dry-run the entry point when safe, in a clean environment.
6. Compare generated output names and values to the manuscript's references and numbers.
7. Record missing software, runtime failures and unverifiable steps.

## 3. A record is not done until it has been reproduced

Capturing code, data, environment, seeds and commands is necessary but not sufficient. Reproduce the result from the record in a clean environment before calling it reproducible. Defer that only when a fresh run is technically impossible (the hardware, proprietary data or licensed software is unavailable), never for lack of time; if a full run is too long, reproduce a minimal subset (fewer steps, one seed) and say so. `references/ensuring-reproducibility.md` has what to capture, where the record lives, the verify step and the red flags.

## 4. Paper-to-code consistency

For a paper with Stata, R or Python code, run the two reviews in `references/review-paper-code.md`: code reproducibility and quality, and a mapping of each main empirical claim (estimate, sample, specification, table or figure) to the code that produces it. Treat gaps as items to verify, not accusations. Use Biorouter's `subagent` tool for the two reviews in parallel when it is offered; otherwise run them in turn.

## 5. Open-science disclosures

Check that:

- Methods are detailed enough for another group to reproduce.
- Inclusion and exclusion criteria are explicit for reviews and cohorts.
- The protocol, preregistration or analysis plan is linked when one exists, and its registration date is consistent with the study dates (`references/registration-timing.md`).
- The data availability statement is accurate, and the code availability statement points to a runnable package.
- Ethical approval (committee and number), consent, privacy and restricted-data constraints are stated.
- Conflicts, funding and licence terms are documented.

## 6. Reporting-guideline check

Pick the guideline from the study type (or use the one the person names):

| Study type | Guideline | Bundled here |
|---|---|---|
| Randomised trial | CONSORT 2025 (plus CONSORT-AI for AI) | CONSORT |
| Trial protocol | SPIRIT 2025 (plus SPIRIT-AI) | SPIRIT |
| Observational study | STROBE (STROBE-MR, RECORD as extensions) | STROBE |
| Diagnostic accuracy | STARD 2015 (STARD-AI for AI) | STARD |
| Prediction model, AI or ML | TRIPOD+AI 2024 (TRIPOD 2015 if no ML; TRIPOD-LLM for LLMs) | TRIPOD+AI |
| Systematic review or meta-analysis | PRISMA 2020, plus PRISMA 2020 for Abstracts | both |
| Animal study | ARRIVE 2.0 | ARRIVE |
| Anything else | see the full table in `references/check-reporting.md` | no |

Then follow `references/check-reporting.md`: run the fail-fast guard (`python3 "$SKILL_DIR/scripts/check_checklist_exists.py" --guideline STROBE`), read the whole manuscript, mark each item PRESENT, PARTIAL or MISSING with the section and a quote, run the PRISMA arithmetic and framework-naming checks where they apply, and write the report from `references/report-templates.md`. A guideline that is not bundled is scored against the official checklist the person supplies; never construct its items from memory unless they accept the NON-AUTHORITATIVE banner.

## 7. Pass criteria

A package passes only if a new analyst can reproduce the public outputs from documented inputs without private knowledge. If data cannot be shared, the package must still include synthetic or sample data, or a documented restricted-data workflow. A paper passes the reporting check only when every mandatory item of its guideline is PRESENT or justified as not applicable.

## Output format

Return a compact audit:

| Check | Status | Evidence | Fix |
|---|---|---|---|

Then:

1. `Reproduction`: what was re-run, where, and whether it matched (or why it was deferred).
2. `Paper-to-code`: matched claims, items to verify, claims not found in the code.
3. `Required disclosures` and `Missing artifacts`.
4. `Reporting checklist`: guideline, version, items PRESENT / PARTIAL / MISSING, and the blocking ones.
5. Verdict: `Ready`, `Ready with restrictions` or `Not ready`, and the next concrete fix.

## Related skills

- `claim-evidence-integrity` traces each claim and citation in the text; this skill checks that the code and data reproduce them.
- `systematic-review-prisma` runs a review; this skill checks its report against PRISMA.
- `research-code-hardening` and the `superpowers` bundle make the code robust before the audit; `empirical-research-router` ends its stage passport here.
