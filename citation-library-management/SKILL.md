---
name: citation-library-management
description: Find papers, pull accurate metadata from DOIs, PMIDs and arXiv ids, verify every reference exists and matches, format clean BibTeX, and manage a Zotero library (collections, tags, attachments, exports) through ZoteroAgent or pyzotero. Use when building or cleaning a bibliography, converting DOIs to BibTeX, checking a reference list for errors or fabricated entries, deduplicating references, or reading from or writing to Zotero.
user-invocable: true
license: Apache-2.0 AND MIT
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876 (skills/citation-management, skills/pyzotero)"
---

# Citation Library Management

A reference list is data, and every entry should be traceable to a registry record (Crossref,
DataCite, PubMed, arXiv), not to memory. This skill finds, verifies, formats and stores
references; the two guides under `references/` are adapted from K-Dense Scientific Agent Skills
(MIT; see `LICENSE-UPSTREAM`).

## The one rule

**Never write a reference from memory.** Every entry comes from a lookup by identifier or a
search result that was opened and checked. If a paper cannot be found in a registry, say so and
leave it out or mark it unverified; do not reconstruct authors, year or pages.

## Choose the route

| Task | Route | Guide |
| --- | --- | --- |
| Search for papers by topic, author or title | LiteratureAgent (OpenAlex, Crossref, PubMed, Semantic Scholar) when installed, else the guide's search scripts | `references/citation-management.md` |
| DOI, PMID or arXiv id to a BibTeX entry | Registry lookup (`doi_to_bibtex.py`, `extract_metadata.py`) | `references/citation-management.md` |
| Check a whole reference list or `.bib` file for errors, missing DOIs, retractions or fabricated entries | `validate_citations.py`, then a manual pass on flagged entries | `references/citation-management/references/citation_validation.md` |
| Format and clean BibTeX: keys, capitalisation braces, duplicates, field order | `format_bibtex.py` | `references/citation-management/references/bibtex_formatting.md` |
| Read, search, tag or organise a Zotero library, export a collection | ZoteroAgent when installed; otherwise pyzotero (web API with a key, or the local API of Zotero 7 or later) | `references/pyzotero.md` |
| Write to Zotero (create items, add notes, move into collections) | ZoteroAgent or pyzotero write API, after the person confirms the change | `references/pyzotero/references/write-api.md` |

## Verification workflow for a reference list

1. Parse the list or `.bib` file into records; keep the original text of each.
2. Resolve each record to an identifier. Use the DOI when present; otherwise search by exact
   title and first author, and accept a match only when title, first author and year agree.
3. Compare the registry metadata with the entry: authors (count and order), title, venue,
   year, volume, pages, DOI. Record every difference.
4. Check status: retractions and corrections (Crossref update metadata, Retraction Watch data in
   Crossref), preprints that have since been published (prefer the published version, cite both
   when the preprint was what was read).
5. Flag entries with no registry match as **unverified**; they are the likeliest fabrications
   and must be checked by the person against the source they actually read.
6. Produce a report: verified, corrected (with the fields changed), unverified, retracted.

## BibTeX that survives a journal's build

- Stable, readable keys (`smith2024tumor`), unique across the file.
- Protect capitalisation that must survive styles with braces: `{RNA}`, `{T} cells`,
  `{Alzheimer}'s`.
- One entry type per kind of work (`@article`, `@inproceedings`, `@misc` for preprints and
  datasets with `eprint` or `howpublished`), DOIs in the `doi` field without the URL prefix.
- No duplicates: deduplicate by DOI, then by normalised title.
- Datasets and software are citable: use their DOIs (Zenodo, Dryad, Figshare) and versions.

## Zotero safety

Reading is safe; writing changes the person's library. Before any write, say what will change
(items, collections, tags), and wait for a yes. Never delete items or empty the trash. API keys
come from the person's own configuration or environment (`ZOTERO_API_KEY`), never from chat
text written into files.

## In Biorouter

- LiteratureAgent is the scholarly search extension; this skill is the method for turning its
  results into verified references. ZoteroAgent holds the Zotero tools, and its bundled skill
  defers here for method.
- Run the guide's scripts with the Developer shell (`references/citation-management/scripts/`);
  they need network access to the registries.
- After references are clean, `claim-evidence-integrity` checks that each cited source supports
  the sentence that cites it. Systematic searches with screening logs belong to
  `systematic-review-prisma`.

## Guides in this skill

| Guide | Covers |
| --- | --- |
| `references/citation-management.md` | Search, metadata extraction, enrichment, BibTeX formatting, validation, where credentials are sent |
| `references/pyzotero.md` | Zotero web and local APIs, authentication, reading, searching, writing, exports, attachments, CLI and MCP |
