---
name: figure-qa
description: "Check a rendered scientific figure before it goes into a paper, poster or slide: size, DPI, fonts embedded and large enough, palette and colour-blind safety, clipped or overlapping text, verbatim labels present, and a visual review of the rendered PNG. Use when the user says check this figure, QA this figure, is this figure ready for the journal, or after you make a figure that will be submitted. Works on PNG, TIFF, JPEG, PDF, SVG and on the Python script that drew the figure."
license: Apache-2.0 AND MIT AND BSD-3-Clause
user-invocable: true
metadata:
  version: "1.0.0"
  origin: "adapted"
  upstream: "Haojae/scipilot-figure-skill@43098ddb9e6a6d142218540c114f9ed38922fc42; K-Dense-AI/scientific-agent-skills@ec59a29a03d5c40f73ab40878df04860bc00e876; neuromechanist/research-skills@1bbc8382711216a39cee05e6e096acbf6b1b6d65; posit-dev/skills@951959403f4ecc9d0274adf35538fc67153b6f31 (see LICENSE-UPSTREAM)"
---

# Figure QA

Check a figure the way a journal's production desk and a careful reviewer would, and report what
to fix. Scripts measure everything that has a ground truth (pixel size, DPI, font types, point
sizes, colours, overlapping boxes, detected text); your own look at the rendered image judges
what only a reader can (hierarchy, clutter, whether the panels read as one figure). Never score
by eye what a script can measure, and never report a measurement a script did not produce.

This skill checks figures. It does not draw them: Python style lives in python-visualization,
R and ggplot2 style in ggplot-visualization.

## 1. Collect the briefing

Before running anything, find or ask for:

- the figure path, and the script that drew it when there is one;
- the target journal (`nature`, `science`, `cell`, `pnas`, `ieee`, `poster`, `slide` or `generic`)
  and the final width (single column, 1.5 columns, double column, in mm or inches);
- every verbatim string the figure must show (panel letters, axis titles, key labels): without
  this list the text check in `check_raster.py` does not run, and a missing label looks like a pass;
- the project's palette, if it has one (a `theme.json`, or a named palette such as `okabe-ito`).

`references/journal-specs.md` lists column widths, minimum font sizes, DPI and panel-label style
for the major journals. Journal rules change, so confirm against the journal's author guide when
the figure is close to a limit.

## 2. Run the programmatic checks

Run the scripts in `scripts/` of this skill with the shell. They are read-only and never change
the figure. Use `uv run --with <package>` when a dependency is missing rather than installing into
the user's environment.

| Input | Command | What it checks |
| --- | --- | --- |
| any file | `uv run --with pillow --with pypdf python scripts/check_figure.py FIG --min-dpi 300 --width-in 3.5 --height-in 2.6 --strict` | format (no JPEG for data plots), DPI metadata, size against the target, PDF font types (Type 42, no Type 3), raster images hidden in SVG |
| PNG, TIFF, JPEG | `uv run --with pillow --with pytesseract python scripts/check_raster.py FIG --journal nature --width-mm 89 --expect-text "a" --palette okabe-ito --json` | resolution, transparency, dominant colours against the palette, OCR of every expected string and its cap height in points |
| SVG | `uv run --with lxml --with svgelements --with shapely python scripts/check_svg.py FIG --json --palette okabe-ito` | fonts, geometry, overlaps, palette (a section that fails to parse is reported as a finding; say so rather than treating it as a pass) |
| Python plot script | `python scripts/check_plot_script.py plot.py --journal nature` | rcParams font sizes, `savefig` settings, library choice |
| matplotlib `Figure` in a script you control | `from visual_qa import audit_layout, render_preview` | missing glyphs, text clipped at the canvas edge, overlapping tick labels; writes a PNG preview |
| the palette used | `python scripts/palette_audit.py --color '#0072B2' --color '#E69F00' --background '#FFFFFF'` (or `--palette <name>`, `--list-palettes`) | contrast against the background and grayscale separation of each pair of colours |
| any raster image | `python scripts/image_metadata.py FIG` | embedded DPI, physical size in mm, colour mode, ICC profile |

The exit-code contract of `check_raster.py`, `check_svg.py` and `check_plot_script.py`
(0 ship, 1 revise, 2 block) and the full per-branch procedure are in
`references/figure-qa-procedure.md`. `tesseract` must be on the PATH for the OCR check; when it is
not, say the text check did not run. OCR misses small text (legend entries at 6 to 7 pt are often not
read at 300 DPI), so treat a `text_missing` finding on small labels as "check by eye", and confirm it
in step 3. The upstream scripts phrase some hints for figures made by an image model ("add literal
on-image text via the model prompt"); for a figure drawn by code, fix the code instead.

## 3. Look at the rendered figure

Render the figure to a PNG at about 150 DPI at its final size (`render_preview()` in
`scripts/visual_qa.py` does this for a matplotlib figure or a raster file; for a PDF use
`pdftoppm -png -r 150` or PyMuPDF), then open the PNG with Developer's `image_processor` tool (or
another image-reading tool your chat has) and judge:

- does the eye go first to the main result, and is there one main point per figure?
- do legends, labels or significance marks cover data?
- do panel letters line up and follow the journal's style?
- do colours still separate in grayscale and for colour-blind readers?
- is anything decorative that carries no data (3D effects, heavy grids, shadows)?

If you cannot view images in this chat, say so, skip this step, and report the figure as checked
by scripts only. Do not guess at what the figure looks like.

## 4. Check the words that go with the figure

- The caption states the error type (SD, SEM, 95% CI, IQR), n, the test and its correction, and
  what the significance marks mean.
- Every number on the figure matches the source table or the script's output.
- The figure has alt text for the web, the journal's accessibility statement or a pkgdown site:
  `references/alt-text.md` explains how to write it (chart type, axes, the main pattern, the
  takeaway).

`references/publication-checklist.md` is the full pre-submission list, including the semantic
pitfalls (mean bars on small samples, dual y-axes, pies and 3D, truncated axes, rainbow colour
maps).

## 5. Report

Report in this order: the input type and which checks ran (and which did not, with the reason);
every FAIL and WARN with the measured value, the limit and the fix; your visual findings; then a
verdict: **ship**, **revise** or **block**. End with one fenced JSON block in the shape
`references/figure-qa-procedure.md` defines (`status`, `findings[]` with `check`, `severity`,
`message`, `action`, `hint`, plus `measurements`), so a script or another skill can act on it.

When you also made the figure, fix one finding at a time (the highest-leverage one first), render
again and re-run the checks, and stop at **ship** or after three rounds. A check is more
trustworthy from a reviewer that did not make the figure: when subagents are available, give a
fresh subagent the briefing from step 1 and this skill, and let it do steps 2 to 5.
