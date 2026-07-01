---
name: claim-evidence-integrity
description: Check that a manuscript, report, slide deck, or analysis summary has every major claim, number, table, figure, and citation grounded in evidence. Use before finalizing research prose or when auditing consistency between results and text.
user-invocable: true
license: Apache-2.0
---

# Claim Evidence Integrity

Source adaptation: BioRouter-original synthesis from Auto-Empirical Research Skills consistency audits and Scientific Agent Skills citation/reporting patterns, rewritten under Apache-2.0.

Use this skill as a final integrity pass for research deliverables.

## Register The Evidence

Create a ledger with:

- Headline claims.
- Numeric results and units.
- Sample sizes and exclusions.
- Table/figure references.
- Citation-backed background claims.
- Limitations and uncertainty statements.

Each item must point to a source: raw computation, table, figure, dataset, script, paper identifier, or user-provided fact.

## Checks

- Numbers in prose match tables/figures exactly.
- Units and denominators are consistent.
- Sign, direction, confidence intervals, p-values, and significance markers match.
- Sample sizes do not drift across abstract, methods, tables, and captions without explanation.
- Causal language matches the identification gate.
- Every cited claim is supported by the cited source, not merely related to it.
- Every table and figure is referenced in order and has a corresponding generation script when applicable.

## Fail Conditions

Do not approve the document when:

- A headline result cannot be traced to a computation or table.
- A causal conclusion is based on a design that only supports association.
- A citation exists but does not support the sentence.
- Results generated from different samples are compared as if they used the same cohort.

## Output Format

Return:

1. `Integrity verdict`: pass, pass with caveats, or fail.
2. `Blocking issues`: exact claims/numbers and evidence gaps.
3. `Non-blocking issues`: clarity or formatting issues.
4. `Correction plan`: concrete edits or computations needed.
