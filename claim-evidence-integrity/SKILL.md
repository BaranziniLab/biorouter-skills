---
name: claim-evidence-integrity
description: "Check that a manuscript, report, grant, slide deck or analysis summary has every major claim, number, table, figure and citation grounded in evidence, and that every citation is real, supports its sentence and is current enough for the claim. Runs a reference verifier against PubMed, CrossRef and OpenAlex that flags fabricated or mismatched references. Use before finalizing research prose, when auditing consistency between results and text, or when fabricated or stale references would be harmful."
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "Aperivue/medsci-skills/skills/verify-refs@7e9d133dd0216c29b0e030729e3719c3db5e0973"
---

# Claim Evidence Integrity

Source adaptation: Biorouter-original audit (ideas from Auto-Empirical Research Skills consistency audits and Scientific Agent Skills citation patterns, no text copied), plus the reference verifier and claim-fidelity checker from Aperivue/medsci-skills `verify-refs` (MIT; see `LICENSE-UPSTREAM`).

Use this skill as the final integrity pass for research deliverables. It has three parts: the evidence ledger (every claim and number traced to a source), the citation and temporal checks (every reference real, supporting and current), and the runnable verifier that does the bibliographic part without relying on memory.

This skill replaces `citation-temporal-integrity`. If that skill is also installed, it is an earlier version of the citation part of this one and should yield to it.

**House rule.** Never rely on memory for a bibliographic fact or a number. Retrieve it, compute it, or mark it unverified.

## 1. Register the evidence

Create a ledger with:

- Headline claims.
- Numeric results and units.
- Sample sizes and exclusions.
- Table and figure references.
- Citation-backed background claims.
- Limitations and uncertainty statements.

Each item must point to a source: raw computation, table, figure, dataset, script, paper identifier, or user-provided fact.

## 2. Claim and number checks

- Numbers in prose match tables and figures exactly.
- Units and denominators are consistent.
- Sign, direction, confidence intervals, p-values and significance markers match.
- Sample sizes do not drift across abstract, methods, tables and captions without explanation.
- Causal language matches the identification design (`causal-identification-gates` when it is installed).
- Every table and figure is referenced in order and has a corresponding generation script when applicable.
- Results generated from different samples are not compared as if they used the same cohort.

## 3. Citation checks

For each citation, verify:

- Title, authors, year, venue, and a DOI, PMID, arXiv or OpenAlex identifier.
- The source exists and the identifier resolves (run the verifier, section 5).
- The authors in the citation are the source's authors, at every position, not only the first.
- The cited paper actually supports the sentence, not merely relates to it. Quoted text, attributed concepts and stated counts can be checked against downloaded full texts (section 5).
- Retractions, expressions of concern and major corrections are absent. Check the publisher page or PubMed's "Retracted" and "Comment in" links for every load-bearing citation.
- The same work is not listed twice under two entries.

## 4. Temporal checks

Flag:

- "Recent", "latest" or "current" claims without a date-bounded search behind them.
- Clinical or regulatory statements older than the current guideline cycle.
- Methods claims that ignore newer best-practice estimators.
- A claim contradicted by newer high-quality evidence.
- Anachronistic citations: a cited work that postdates the claim it supports, or a later review cited for a historical first.
- `in press`, `forthcoming`, `TBD` or `e000` pagination that has since been resolved.

## 5. Run the reference verifier

The scripts in `scripts/` are standard-library Python 3 and need no install. Set `SKILL_DIR` to the skill directory Biorouter lists when this skill loads, then run from the project root through the Developer shell (the wrapper writes `qc/` under the nearest folder above the manuscript that contains `submission/`, or else beside the manuscript):

```bash
python3 "$SKILL_DIR/scripts/verify_refs.py" manuscript.md --project-root .
"$SKILL_DIR/scripts/verify_cli.sh" refs.bib --strict      # before submission
"$SKILL_DIR/scripts/verify_cli.sh" refs.bib --offline     # parse and classify only, no network
```

Inputs: `.md`, `.docx` (needs `python-docx`), `.bib`, `.txt` or `.tsv`. Output: `qc/reference_audit.json`, with one record per reference whose `status` is `OK`, `MISMATCH` (the work exists, the citation is wrong), `FABRICATED` (the identifier does not exist and nothing found the work) or `UNVERIFIED` (nothing confirmed or refuted it). Every verdict comes from that file; never mark a row `OK` yourself. The verifier never edits the bibliography.

The verifier sends each identifier and title to PubMed, CrossRef, doi.org and OpenAlex. It sends no manuscript text. A contact address for those services is optional (`MEDSCI_CONTACT_EMAIL` or `NCBI_EMAIL`); without one it sends a generic placeholder, and `NCBI_API_KEY` raises the PubMed rate limit. Do not set a person's address without asking them.

Quality gates:

1. Stop if any row is `FABRICATED`.
2. Stop if any row is `MISMATCH`; correct the citation through the reference manager.
3. Ask the person before accepting any `UNVERIFIED` reference, and say how it was checked by hand.
4. Rerun after any reference edit.

Claim fidelity: `scripts/check_claim_fidelity.py` checks quoted text, attributed concepts and stated counts against full texts you have already downloaded and converted to text. It never fetches anything, and silence means "nothing checkable was wrong", not "everything is right".

Read on demand:

- `references/reference-verifier.md`: every option, the output contract, the author cross-check and the DOI decision table.
- `references/manual-checkpoints.md`: when to run `--strict`, and what to do for each status.
- `references/claim-fidelity-workflow.md`: the sentence-level source evidence table and how to record an assessment honestly.

## 6. Fail conditions

Do not approve the document when:

- A headline result cannot be traced to a computation or table.
- A causal conclusion rests on a design that only supports association.
- A citation exists but does not support the sentence.
- Any reference is `FABRICATED` or `MISMATCH`, or an `UNVERIFIED` one was not confirmed by hand.
- A load-bearing citation is retracted or superseded by newer evidence that the text ignores.

## Output format

Return:

1. `Integrity verdict`: pass, pass with caveats, or fail.
2. `Blocking issues`: exact claims, numbers and references, with the evidence gap for each.
3. `Citation ledger`:

| Claim | Citation | Identifier | Verifier status | Supports claim? | Temporal status | Action |
|---|---|---|---|---|---|---|

   Allowed actions: keep, replace, add stronger source, qualify, remove claim, or live search required.
4. `Non-blocking issues`: clarity or formatting.
5. `Correction plan`: concrete edits or computations needed.

## Related skills

- `scientific-research` calls this skill for its verification stage.
- `systematic-review-prisma` owns literature search and screening; this skill audits what was cited.
- `scientific-manuscript-writing` drafts; `scientific-prose-review` line-edits; `anti-ai-writing` removes AI tells. None of them check evidence; this one does.
- `replication-package-audit` checks that the code and data reproduce the numbers this skill traces.
