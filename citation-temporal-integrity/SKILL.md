---
name: citation-temporal-integrity
description: Verify that citations are real, relevant, current enough for the claim, and temporally valid. Use for literature reviews, manuscripts, grant text, reports, and any task where fabricated or stale references would be harmful.
user-invocable: true
license: Apache-2.0
---

# Citation Temporal Integrity

Source adaptation: BioRouter-original synthesis from Auto-Empirical Research Skills citation hygiene and Scientific Agent Skills literature workflows, rewritten under Apache-2.0.

Never rely on memory for bibliographic facts. Use live retrieval when available.

## Citation Checks

For each citation, verify:

- Title, authors, year, venue, DOI/PMID/arXiv/OpenAlex ID.
- The source exists and the identifier resolves.
- The cited paper actually supports the sentence.
- The claim is not contradicted by newer high-quality evidence.
- Retractions, expressions of concern, or major corrections are absent.
- The cited work predates the claim it is used to support.

## Temporal Checks

Flag:

- "Recent", "latest", or "current" claims without a date-bounded search.
- Clinical or regulatory statements older than the current guideline cycle.
- Methods claims that ignore newer best-practice estimators.
- Citations used anachronistically, such as citing a later review for a historical claim.

## Output Format

Return a citation ledger:

| Claim | Citation | Identifier | Supports claim? | Temporal status | Action |
|---|---|---|---|---|---|

Allowed actions: keep, replace, add stronger source, qualify, remove claim, or live-search required.
