---
name: scientific-artifacts
description: Plan and produce research artifacts such as DOCX manuscripts, PDF reports, PPTX slide decks, XLSX result workbooks, LaTeX posters, scientific schematics, and figure packages with reproducible source mapping. Use when the user wants publication or presentation files rather than only analysis code.
user-invocable: true
license: Apache-2.0
---

# Scientific Artifacts

Source adaptation: BioRouter-original synthesis from Scientific Agent Skills document/slide/poster patterns and Auto-Empirical Research Skills exhibit mapping, rewritten under Apache-2.0.

Use this skill when the deliverable is a file or polished artifact.

## Artifact Contract

Before creating files, state:

- Format: DOCX, PDF, PPTX, XLSX, LaTeX, Markdown, HTML, or image.
- Audience and venue.
- Required sections.
- Data/source files that support each table or figure.
- Visual style constraints.
- Verification path: render, inspect, and confirm no missing references.

## Exhibit Mapping

For every table or figure, keep:

| Exhibit | Source data/script | Output file | Claim supported |
|---|---|---|---|

Do not create a polished artifact whose numbers are not traceable.

## Quality Gates

- Render the artifact when tooling is available.
- Check cross-references, captions, page overflow, table readability, and broken links.
- Verify that all citations and claims pass `citation-temporal-integrity` and `claim-evidence-integrity`.
- Include source files and regeneration steps when the artifact depends on analysis results.
