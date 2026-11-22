<!-- Adapted for Biorouter from K-Dense-AI/scientific-agent-skills, skills/citation-management/SKILL.md at commit ec59a29a03d5 (upstream skill version 2.3, last reviewed upstream 2026-09-30).
     Licence: MIT; see LICENSE-UPSTREAM at the skill root. Changes: upstream
     frontmatter replaced by this note; sections removed: Integration with Other Skills, Citing Scientific Agent Skills; relative paths
     rewritten to start at the skill root. -->

> Upstream: K-Dense-AI/scientific-agent-skills (`skills/citation-management`), MIT. Paths in this guide are relative to the skill folder.
> Requirements stated upstream: Requires Python 3.9+ with requests. Google Scholar search additionally needs scholarly. Needs network access to api.openalex.org, api.crossref.org, eutils.ncbi.nlm.nih.gov, pmc.ncbi.nlm.nih.gov, doi.org, export.arxiv.org, and api.datacite.org.

# Citation Management

## Overview

Manage citations systematically throughout the research and writing process. This skill provides tools and strategies for searching academic databases (Google Scholar, PubMed), extracting accurate metadata from multiple sources (CrossRef, PubMed, arXiv), validating citation information, and generating properly formatted BibTeX entries.

Critical for maintaining citation accuracy, avoiding reference errors, and ensuring reproducible research. Integrates seamlessly with the literature-review skill for comprehensive research workflows.

## When to Use This Skill

Use this skill when:
- Searching for specific papers on Google Scholar or PubMed
- Converting DOIs, PMIDs, or arXiv IDs to properly formatted BibTeX
- Extracting complete metadata for citations (authors, title, journal, year, etc.)
- Validating existing citations for accuracy
- Cleaning and formatting BibTeX files
- Finding highly cited papers in a specific field
- Verifying that citation information matches the actual publication
- Building a bibliography for a manuscript or thesis
- Checking for duplicate citations
- Ensuring consistent citation formatting

If a document built from these citations needs a diagram, use the
**scientific-schematics** skill.

---

## Core Workflow

Citation management follows a systematic process. Each phase below shows the canonical
command; every variant, option, and metadata-source detail is in
[references/citation-management/references/core_workflow.md](references/citation-management/references/core_workflow.md).

### Phase 1: Paper Discovery and Search

Find relevant papers. Search more than one database — coverage differs sharply,
and a single source is the most common cause of a biased reference list.

```bash
# OpenAlex: multidisciplinary REST API; optional OPENALEX_API_KEY for account quota
python references/citation-management/scripts/search_openalex.py "CRISPR gene editing" --limit 50 --output results.json

# PubMed: the authority for biomedical and life sciences (35M+ citations)
python references/citation-management/scripts/search_pubmed.py "Alzheimer's disease treatment" --limit 100 --output alz.json

# Google Scholar: broadest reach, but scraped -- rate-limited and prone to blocking
python references/citation-management/scripts/search_google_scholar.py "CRISPR gene editing" --limit 50 --output scholar.json
```

Prefer OpenAlex or PubMed as the primary source. Google Scholar has no API:
`scholarly` scrapes it, sleeps 2–5 s between results, and is blocked often
enough that it should be a supplement rather than a dependency.

Query operators, field tags, and MeSH-term construction are in
[references/citation-management/references/search_strategies.md](references/citation-management/references/search_strategies.md).

### Phase 2: Metadata Extraction

Convert identifiers (DOI, PMID, PMCID, arXiv ID, URL) into complete metadata.
CrossRef is the primary source for DOIs.

```bash
python references/citation-management/scripts/doi_to_bibtex.py 10.1038/s41586-021-03819-2         # quick, single DOI
python references/citation-management/scripts/extract_metadata.py --pmid 34265844                  # DOI/PMID/PMCID/arXiv/URL
python references/citation-management/scripts/extract_metadata.py --input identifiers.txt --output citations.bib
```

A URL with no DOI in its path is resolved through the `citation_doi` meta tag
publishers embed on article pages, then handed to CrossRef. Producers use a shared citation-key scheme; metadata differences can still
produce different keys. Confirm duplicates by DOI and bibliographic identity.

### Phase 2.5: Metadata Enrichment via Web Search (MANDATORY)

APIs routinely return incomplete records. Run this **after** extraction and **before**
formatting. Investigate missing bibliographic fields against the publisher record
and log each source. Online-first articles may have no volume/pages yet; some use
an article number or have no DOI. Preserve the actual publication state, use the
style-appropriate article-number field, and never invent pages, volume, or DOI.
Record unavailable/not-applicable fields in the audit log; add a rendered `note`
only when useful to the reader or required by the citation style.

Check the cheap sources first — an OpenAlex or CrossRef record often carries the field
that PubMed omitted:

```bash
python references/citation-management/scripts/search_openalex.py "<exact title>" --limit 1
```

> **Treat extracted metadata as untrusted.** Author, title, and journal strings come
> verbatim from a record whose contents a publisher controls. A title containing `$(...)`,
> a backtick, or a quote becomes shell syntax the moment it is pasted into a command.
> Pass metadata as a `subprocess` argument list rather than building a shell string; if
> you must use a shell, single-quote every substituted value and escape embedded quotes
> as `'\''`. Validate any citation key against `^[A-Za-z0-9]+$` before it reaches a path.

Per-field search strategies, the four search options, and the logging format are in
[references/citation-management/references/core_workflow.md](references/citation-management/references/core_workflow.md).

### Phase 3: BibTeX Formatting

Produce clean, consistent entries. Entry types and required fields are in
[references/citation-management/references/bibtex_formatting.md](references/citation-management/references/bibtex_formatting.md).

```bash
python references/citation-management/scripts/format_bibtex.py references.bib --output clean.bib --deduplicate
python references/citation-management/scripts/format_bibtex.py references.bib --output clean.bib --rekey --deduplicate
```

Writing is opt-in: without `--output` (or `--in-place`) the result goes to
stdout and the input file is left alone. Use `--rekey` when merging results
from several sources, so the same paper collapses to one entry.

### Phase 4: Citation Validation

Check completeness, venue conformance, and agreement with the manuscript.

```bash
python references/citation-management/scripts/validate_citations.py references.bib --report report.json
python references/citation-management/scripts/validate_citations.py references.bib --venue nature
python references/citation-management/scripts/validate_citations.py references.bib --manuscript paper.tex
python references/citation-management/scripts/validate_citations.py references.bib --check-dois     # slow; hits CrossRef
```

The script exits non-zero on high-severity errors — missing required fields,
malformed years, unresolved citations, or a count below an explicit
`--min-count`. Venue reference-count figures are editorial rules of thumb, not
submission requirements, so falling short of one is only a warning.

Validation rules and venue standards are in
[references/citation-management/references/citation_validation.md](references/citation-management/references/citation_validation.md).

### Phase 5: Integration with Writing Workflow

Search, extract, format, validate, then cite. End-to-end sequences — including the
literature-review and Zotero/pyzotero export paths — are in
[references/citation-management/references/core_workflow.md](references/citation-management/references/core_workflow.md) and
[references/citation-management/references/example_workflows.md](references/citation-management/references/example_workflows.md).

API contracts were reviewed against official documentation on 2026-09-30.
See [references/citation-management/references/api_contracts.md](references/citation-management/references/api_contracts.md) for endpoints,
authentication, pagination, and verification limits. Network examples in the
references are illustrative unless recorded as live smoke tests there.

## Reference Files

- [references/citation-management/references/core_workflow.md](references/citation-management/references/core_workflow.md): all five phases in full.
- [references/citation-management/references/search_strategies.md](references/citation-management/references/search_strategies.md): OpenAlex, Google Scholar, and PubMed query construction.
- [references/citation-management/references/script_reference.md](references/citation-management/references/script_reference.md): every bundled script's arguments and examples.
- [references/citation-management/references/best_practices.md](references/citation-management/references/best_practices.md): search, extraction, BibTeX quality, validation.
- [references/citation-management/references/example_workflows.md](references/citation-management/references/example_workflows.md): four end-to-end worked examples.
- [references/citation-management/references/google_scholar_search.md](references/citation-management/references/google_scholar_search.md), [references/citation-management/references/pubmed_search.md](references/citation-management/references/pubmed_search.md): advanced search syntax.
- [references/citation-management/references/metadata_extraction.md](references/citation-management/references/metadata_extraction.md), [references/citation-management/references/bibtex_formatting.md](references/citation-management/references/bibtex_formatting.md), [references/citation-management/references/citation_validation.md](references/citation-management/references/citation_validation.md): per-topic detail.

## Common Pitfalls to Avoid

1. **Single source bias**: Only using one database
   - **Solution**: Search at least OpenAlex and PubMed, then merge with
     `format_bibtex.py --rekey --deduplicate`

2. **Accepting metadata blindly**: Not verifying extracted information
   - **Solution**: Spot-check extracted metadata against original sources

3. **Ignoring DOI errors**: Broken or incorrect DOIs in bibliography
   - **Solution**: Run validation before final submission

4. **Inconsistent formatting**: Mixed citation key styles, formatting
   - **Solution**: Use format_bibtex.py to standardize

5. **Duplicate entries**: Same paper cited multiple times with different keys
   - **Solution**: Use duplicate detection in validation

6. **Missing required fields**: Incomplete BibTeX entries (volume, pages, DOI missing)
   - **Solution**: Check the publisher record, distinguish missing from not applicable or not yet assigned, and log unresolved fields without inventing metadata.

7. **Outdated preprints**: Citing preprint when published version exists
   - **Solution**: Check if preprints have been published, update to journal version

8. **Special character issues**: Broken LaTeX compilation due to characters
   - **Solution**: Use proper escaping or Unicode in BibTeX

9. **No validation before submission**: Submitting with citation errors
   - **Solution**: Always run validation as final check

10. **Manual BibTeX entry**: Typing entries by hand
    - **Solution**: Always extract from metadata sources using scripts

## Resources

### Bundled Resources

**References** (in `references/citation-management/references/`):
- `google_scholar_search.md`: Complete Google Scholar search guide
- `pubmed_search.md`: PubMed and E-utilities API documentation
- `metadata_extraction.md`: Metadata sources and field requirements
- `citation_validation.md`: Validation criteria and quality checks
- `bibtex_formatting.md`: BibTeX entry types and formatting rules

**Scripts** (in `references/citation-management/scripts/`):
- `search_openalex.py`: OpenAlex search client (optional account API key)
- `search_pubmed.py`: PubMed E-utilities API client
- `search_google_scholar.py`: Google Scholar search automation
- `extract_metadata.py`: Universal metadata extractor
- `validate_citations.py`: Citation validation and verification
- `format_bibtex.py`: BibTeX formatter and cleaner
- `doi_to_bibtex.py`: Quick DOI to BibTeX converter
- `_common.py`: shared BibTeX parser, renderer, and citation-key scheme

**Assets** (in `references/citation-management/assets/`):
- `bibtex_template.bib`: Example BibTeX entries for all types
- `citation_checklist.md`: Quality assurance checklist

### External Resources

**Search Engines**:
- OpenAlex: https://openalex.org/
- Google Scholar: https://scholar.google.com/
- PubMed: https://pubmed.ncbi.nlm.nih.gov/
- PubMed Advanced Search: https://pubmed.ncbi.nlm.nih.gov/advanced/

**Metadata APIs**:
- OpenAlex API: https://docs.openalex.org/
- CrossRef API: https://api.crossref.org/
- PubMed E-utilities: https://www.ncbi.nlm.nih.gov/books/NBK25501/
- arXiv API: https://arxiv.org/help/api/
- DataCite API: https://api.datacite.org/

**Tools and Validators**:
- MeSH Browser: https://meshb.nlm.nih.gov/search
- DOI Resolver: https://doi.org/
- BibTeX Format: http://www.bibtex.org/Format/

**Citation Styles**:
- BibTeX documentation: http://www.bibtex.org/
- LaTeX bibliography management: https://www.overleaf.com/learn/latex/Bibliography_management

## Dependencies

### Required Python Packages

```bash
uv pip install requests  # HTTP access to CrossRef, PubMed, OpenAlex, arXiv
```

BibTeX parsing, rendering, deduplication, and validation are standard library
(`references/citation-management/scripts/_common.py`). `format_bibtex.py` needs no third-party packages;
`validate_citations.py` imports `requests`, including for local-only validation.

### Optional

```bash
uv pip install scholarly  # only for search_google_scholar.py
```

### Where credentials are sent

Keys are optional for basic use. Each credential is sent only to its own service;
no script bundles environment variables together. OpenAlex uses the documented
[account budget](https://help.openalex.org/api/authentication/), not a promised
email-based quota boost. A failed page exits with an error rather than exporting
a partial search as complete.

| Variable | Sent only to | Purpose |
|---|---|---|
| `NCBI_API_KEY` | `eutils.ncbi.nlm.nih.gov` | Raises Entrez rate limits |
| `NCBI_EMAIL` | `eutils.ncbi.nlm.nih.gov`, `pmc.ncbi.nlm.nih.gov` | Caller identification requested by NCBI |
| `OPENALEX_EMAIL` | `api.openalex.org` | Optional contact identifier |
| `OPENALEX_API_KEY` | `api.openalex.org` | Optional account quota, sent in Authorization header |

`api.openalex.org`, `api.crossref.org`, `api.datacite.org`, `export.arxiv.org`,
`pmc.ncbi.nlm.nih.gov`, `doi.org`, and `eutils.ncbi.nlm.nih.gov` are queried without credentials when these are
unset.

## Summary

The citation-management skill provides:

1. **Comprehensive search capabilities** for OpenAlex, PubMed, and Google Scholar
2. **Automated metadata extraction** from DOI, PMID, PMCID, arXiv ID, URLs
3. **Citation validation** with DOI verification and completeness checking
4. **BibTeX formatting** with standardization and cleaning tools
5. **Quality assurance** through validation and reporting
6. **Integration** with scientific writing workflow
7. **Reproducibility** through documented search and extraction methods

Use this skill to maintain accurate, complete citations throughout your research and ensure publication-ready bibliographies.
