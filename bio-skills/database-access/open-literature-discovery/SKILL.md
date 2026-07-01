---
name: database-access-open-literature-discovery
description: Discover and verify scholarly literature through PubMed, Crossref, OpenAlex, Semantic Scholar, arXiv, bioRxiv/medRxiv, Unpaywall, and DOI/PMID identifiers while avoiding fabricated references and stale claims.
tool_type: mixed
primary_tool: openalex
user-invocable: false
license: Apache-2.0
---

# Open Literature Discovery

Use this skill when a research question needs current, verified literature.

## Retrieval Rules

- Prefer stable identifiers: DOI, PMID, PMCID, arXiv ID, OpenAlex ID.
- Record query, date, database, and filters.
- Separate peer-reviewed articles, preprints, reviews, guidelines, and datasets.
- Verify title, authors, year, and venue before citing.
- Use `citation-temporal-integrity` for final citation checks.

## Workflow

1. Translate the question into database-specific queries.
2. Search at least one biomedical and one broad scholarly index when appropriate.
3. Deduplicate by DOI/PMID/title.
4. Screen for relevance and study type.
5. Extract the citation ledger and key findings.
6. Flag unresolved, retracted, or inaccessible sources.

## Output

Return a table:

| Source | Identifier | Type | Why relevant | Supports which claim |
|---|---|---|---|---|

Do not invent a citation to fill a gap; report the gap.

## Related Skills

- `citation-temporal-integrity`
- `scientific-research`
- `database-access/entrez-search`
