---
name: scientific-artifacts
description: "Plan, produce and verify research deliverables with every number traced to its source: DOCX manuscripts, PDF reports, PPTX slide decks and posters, XLSX result workbooks, LaTeX Beamer talks, scientific schematics and diagrams (flowcharts, pathways, timelines, architecture, Venn, quadrants and more as HTML/SVG), Markdown documents with Mermaid diagrams, visual abstracts and figure packages. Use when the user wants publication or presentation files, slides, a poster, a schematic or a diagram rather than only analysis code."
user-invocable: true
license: Apache-2.0 AND MIT AND CC0-1.0
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "cathrynlavery/diagram-design/skills/diagram-design@d74d8c2d0c78a9e1efd43137f6a9a51182a8b5f0 (2.6); K-Dense-AI/scientific-agent-skills/skills/pptx-posters, scientific-slides, markdown-mermaid-writing@ec59a29a03d5c40f73ab40878df04860bc00e876"
---

# Scientific Artifacts

Source adaptation: Biorouter-original artifact contract and exhibit mapping (ideas from Scientific Agent Skills and Auto-Empirical Research Skills, no text copied), plus four bundled guides adapted from cathrynlavery/diagram-design (MIT, with MIT and CC0 icons) and K-Dense-AI/scientific-agent-skills (`pptx-posters` and `scientific-slides`, MIT, without their image-generation paths; `markdown-mermaid-writing`, Apache-2.0). Licences and changes are in `LICENSE-UPSTREAM`.

Use this skill when the deliverable is a file, a slide deck, a poster or a visual, not only analysis output.

This skill replaces `scientific-visual-communication`. If that skill is also installed, it is an earlier version of the visual part of this one and should yield to it.

Set `SKILL_DIR` to the skill directory Biorouter lists when this skill loads. Each bundled guide is a folder with a `GUIDE.md`; paths inside a guide are relative to its own folder.

## 1. Artifact contract

Before creating files, state:

- Format: DOCX, PDF, PPTX, XLSX, LaTeX, Markdown, HTML, SVG or image.
- Audience and venue (journal, conference talk, lab meeting, poster session, grant panel).
- Required sections, size and length limits (slide count and minutes, poster dimensions, word limits).
- The data and source files that support each table, figure and number.
- Visual style constraints (journal, institution template, colour rules).
- Verification path: render, inspect, and confirm nothing is missing or overflows.

## 2. Exhibit and visual mapping

For every table, figure, schematic element or slide claim, keep:

| Exhibit | Source data, script or citation | Output file | Claim supported |
|---|---|---|---|

Do not create a polished artifact whose numbers are not traceable. A schematic needs the same discipline: every box, arrow and label names the source (a paper, a dataset, a method section) it depicts, and nothing is drawn that the source does not support.

## 3. Pick the route

| Deliverable | Route |
|---|---|
| Word, Excel, PowerPoint or PDF file mechanics (create, edit, convert, fill) | Biorouter's built-in `office-word`, `office-excel`, `office-powerpoint`, `office-pdf` skills, or the BiorOffice extension when installed |
| A talk or slide deck (structure, timing, design, Beamer) | `scientific-slides/` (below) for content and design; the office skill or BiorOffice for the file |
| A research poster as one editable PPTX slide | `pptx-posters/GUIDE.md` |
| A schematic or diagram as HTML/SVG (flowchart, sequence, state machine, ER, pathway, timeline, swimlane, quadrant, Venn, pyramid, tree, layer stack, architecture and more) | `diagram-design/GUIDE.md` |
| A Markdown document, report or README with Mermaid diagrams | `markdown-mermaid/GUIDE.md` |
| A data plot or multi-panel figure | `ggplot-visualization` (R) or `python-visualization` (Python), then `figure-qa`; the built-in Auto Visualiser for an interactive figure in the chat |
| A manuscript's text | `scientific-manuscript-writing`, then this skill for the file |

## 4. Bundled guides

- **`diagram-design/GUIDE.md`**: about 50 diagram types as standalone HTML/SVG with a type picker, layout and typography rules, icons (Tabler, Devicon and log-z/logos, MIT; Simple Icons, CC0), extractors for Mermaid, PlantUML, draw.io and Excalidraw sources, and `scripts/self_check.py` and `scripts/verify_geometry.py` to check a diagram before handing it over. Run its scripts from its folder: `cd "$SKILL_DIR/diagram-design"`. Its example pages and `scripts/export_svg.py` load web fonts from Google Fonts when rendered; no font file is bundled.
- **`pptx-posters/GUIDE.md`**: a strict JSON manifest that generates one real `.pptx` poster slide, with layout, palette and image checks and a security review of the file; it uses no network, no API keys and no image-generation service. Run its scripts from `"$SKILL_DIR/pptx-posters"`.
- **`scientific-slides/`**: reference only, no GUIDE.md. `references/presentation_structure.md`, `talk_types_guide.md`, `slide_design_principles.md`, `data_visualization_slides.md`, `presentation_workflow.md`, `visual_review_workflow.md`, `common_pitfalls.md` and `beamer_guide.md`; `assets/` holds Beamer templates (conference, seminar, defense), timing guidelines and a PowerPoint design guide; `scripts/validate_presentation.py` checks a deck and `slides_to_pdf.py` combines slide images into a PDF; render pages for visual review with `pdftoppm -png -r 110 deck.pdf page` or LibreOffice (the upstream `pdf_to_images.py` needs the AGPL PyMuPDF and is not included). The upstream skill's AI image-generation workflow is not included: build slides from real figures, tables and text.
- **`markdown-mermaid/GUIDE.md`**: a Markdown style guide, a Mermaid style guide with one reference per diagram type, and document templates (research paper, report, how-to, pull request, presentation).

## 5. Quality gates

- Render the artifact when tooling is available (LibreOffice, a PDF renderer, a browser, `pdflatex`), and look at the rendered pages, not only the source.
- Check cross-references, captions, page and slide overflow, text size at the viewing distance, table readability and broken links.
- Run `claim-evidence-integrity` on every claim, number and citation in the artifact.
- Visuals: colourblind-safe palette, labels readable at the final size, no decorative element that implies data, and alt text for every figure in a digital deliverable.
- Include source files and regeneration steps when the artifact depends on analysis results.
- Mark anything that needs credentials, proprietary data, wet-lab execution or a live service as unverified unless it was actually checked.

## Output

Return the files with their paths, the exhibit map, what was rendered and checked, and anything left unverified.
