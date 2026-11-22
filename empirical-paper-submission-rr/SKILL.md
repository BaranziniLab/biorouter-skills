---
name: empirical-paper-submission-rr
description: Take an economics or social-science paper through submission and a revise-and-resubmit, covering the submission package (anonymised manuscript, online appendix, cover letter, JEL codes, disclosures, data availability), AEA-style replication packages, triage of referee reports and the editor's letter into a revision plan, a numbered robustness appendix, marked-up changes, registered-report stages, deadlines and resubmission after rejection. Use when preparing a submission or planning and running an R&R round.
user-invocable: true
license: Apache-2.0
metadata:
  version: "1.1.0"
  origin: native
  upstream: "none (native rewrite, no upstream text copied)"
---

# Empirical Paper Submission and R&R

Most revise-and-resubmit rounds are lost on logistics rather than substance: a request missed in
the third report, a robustness check run but never shown, a replication package that does not
rerun. This skill runs the round as a tracked project. It is written for Biorouter and copies no
upstream text.

Drafting the point-by-point replies themselves, and refereeing other people's papers, belong to
`manuscript-peer-review`. Choosing the venue belongs to `research-evaluation-venues`; writing the
paper to `scientific-manuscript-writing`.

## Before submission: the package

| Item | Notes |
| --- | --- |
| Anonymised manuscript | Remove names, acknowledgements, funding and self-identifying citations if the journal is double-blind; check PDF metadata and file names too |
| Title page | Authors, affiliations, corresponding author, acknowledgements, funding, JEL codes, keywords |
| Online appendix | Numbered sections and tables (A1, A2), each referenced from the main text |
| Cover letter | One page: the question, the main finding, why this journal, and any related submissions or prior rejections the journal asks about |
| Disclosures | Conflicts and funding in the journal's format (AEA journals require a disclosure statement for each author); IRB approval or exemption; pre-registration id (AEA RCT Registry, OSF) for experiments |
| Data availability statement | Where data and code will be deposited, access conditions for restricted data (WRDS, administrative data, confidential surveys) |
| Replication package | Required at acceptance by AEA journals and many others, and better prepared now (below) |

Check the journal's current submission instructions and fees, its preprint policy (NBER, SSRN
and working-paper series are generally fine in economics), and its style for tables (AEA
journals, for example, ask authors not to use significance stars).

## Replication package

Follow the AEA Data Editor's guidance and template README (the Social Science Data Editors'
template is widely accepted):

- one master script that runs everything from raw data to every table and figure, with expected
  run time and hardware;
- software and package versions (Stata `version`, vendored ado files, `renv` lockfile, Python
  lock file);
- a data citation and availability statement for every source, including how to request
  restricted data;
- a list mapping every table and figure to the script and line that produces it.

`replication-package-audit` checks the package from a clean environment; run it before
submission, not after acceptance. Stata and R project structure for this is in
`econometrics-toolkit`.

## When the decision letter arrives

1. **Read the editor's letter first.** It tells you which referee points are required, which are
   optional and which the editor does not share. That ranking overrides the referees' own.
2. **Split every report into numbered comments** in one tracking table: id (R1.3, R2.7), quoted
   comment, type (analysis, framing, writing, data, citation), the editor's priority, decision
   (do, partly do, explain why not), owner, status, and where the change lives (section, table,
   appendix number).
3. **Group overlapping requests** across referees so one new analysis answers several comments,
   and note the cross-references.
4. **Plan the new analyses** with the design in view: run `causal-identification-gates` again
   when a referee challenges identification, and `econometrics-toolkit` for alternative
   estimators or standard errors. Pre-specify what result would change the paper's claims.
5. **Set a calendar** from the resubmission deadline backwards, with a buffer for co-author
   review; ask the editor early if an extension is needed.

## The robustness appendix

Every requested or volunteered robustness check gets a numbered table or figure in the appendix,
a sentence in the main text that states what it shows, and a pointer from the tracking table.
Checks that contradict the main result are reported, not dropped; say how the conclusion changes.
Keep the scripts for each check in the replication package.

## The resubmission

- **Response document**: a short summary of the main changes for the editor, then a section per
  referee with each comment quoted, the reply, and the exact location of the change. Draft the
  replies with `manuscript-peer-review`, using the tracking table as input; keep the tone factual
  and thank referees once, not in every reply.
- **Marked-up manuscript**: a `latexdiff` or tracked-changes version beside the clean one if the
  journal asks for it.
- **Consistency check**: every number that changed in the text matches the new tables
  (`claim-evidence-integrity`), the appendix numbering matches the references, and the abstract
  still states the current result.

## After a rejection

Read the reports for problems that will recur at the next journal and fix those first. Some
journals accept prior reports with a response (AEA journals allow forwarding reports from other
AEA journals); ask before assuming. Do not resubmit the same file unchanged.

## Registered reports

For journals that offer them: Stage 1 submits the introduction, hypotheses, design, analysis plan
and power analysis before data are collected or analysed; in-principle acceptance follows review.
Stage 2 adds results and discussion, with any deviations from the plan reported and justified.
Power and sample-size planning use `statistical-modeling-bayes`; pre-registration documents should
match the Stage 1 plan word for word where they overlap.

## Related skills

- `econometrics-toolkit`, `causal-identification-gates`, `empirical-research-router` for the
  analysis work a revision requires.
- `replication-package-audit` for the package; `claim-evidence-integrity` for the final check.
- `citation-library-management` for the updated reference list.
