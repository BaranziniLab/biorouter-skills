<!-- Translated from Chinese for Biorouter from Haojae/scipilot-figure-skill references/publication_checklist.md (MIT, commit 43098ddb9e6a). Changes: translated to English; links to files not shipped with figure-qa removed; script commands point to this skill's scripts/. See LICENSE-UPSTREAM. -->

# Pre-submission compliance checklist

Tick **every item** for each figure before submission. Any FAIL means the figure is regenerated. `scripts/check_figure.py --strict` is the machine version of this checklist.

> This checklist covers **formal compliance** only (size, DPI, font size, whether error bars are explained). **Semantic** pitfalls (mean bars that hide the distribution, misleading dual y-axes, pie charts and the like) are in the "Semantic compliance" section below; a figure must pass both before submission.

## Contents

- [Size and resolution](#size-and-resolution)
- [File format](#file-format)
- [Fonts and font size](#fonts-and-font-size)
- [Colour and colour blindness](#colour-and-colour-blindness)
- [Axes and labels](#axes-and-labels)
- [Legends and panel labels](#legends-and-panel-labels)
- [Error bars and statistics](#error-bars-and-statistics)
- [Semantic compliance](#semantic-compliance)
- [Extra checks for figures with Chinese text](#extra-checks-for-figures-with-chinese-text)
- [Final check](#final-check)

---

## Size and resolution

- [ ] `figsize` is set directly to the target journal's final size (**single column about 3.5 in, double column about 7.2 in**)
- [ ] The exported file is **not** rescaled again in Word, LaTeX or PowerPoint
- [ ] Raster DPI is at least 300 (ordinary colour) or at least 600 (line art, IEEE)
- [ ] `check_figure.py` confirms the size embedded in the file is within 0.1 in of the target

## File format

- [ ] Data plots (line, bar, scatter, heat map, box plot) are **vector**: PDF, SVG or EPS
- [ ] Micrographs and photographs are **raster**: PNG or TIFF (at least 300 DPI)
- [ ] **No JPEG at all** (never for data plots; prefer TIFF for photographs too)
- [ ] PDFs embed TrueType fonts (**fonttype 42**) and contain no Type 3 fonts
- [ ] SVGs contain **no base64-embedded raster images** (they defeat the point of vector output)

## Fonts and font size

- [ ] The font matches the journal: Nature, Science, Elsevier, PNAS use Helvetica or Arial; IEEE uses Times; Chinese journals use SimSun with Times New Roman
- [ ] At final size, body labels are 7 to 9 pt, tick labels 6 to 8 pt, and the **smallest text is at least 6 pt**
- [ ] Every character renders; there are no empty boxes (always check when the figure has Chinese text)
- [ ] No more than two fonts in one figure

## Colour and colour blindness

- [ ] The default palette is Okabe-Ito or seaborn's `colorblind`; **avoid red against green**
- [ ] Categories are **encoded twice**: different colour and different line style or marker
- [ ] A grayscale preview is exported and the categories are still distinguishable in it
- [ ] Heat maps use a **perceptually uniform** colour map (viridis, magma, inferno, cividis, RdBu_r), **not** rainbow or jet
- [ ] Data with two directions use a diverging colour map centred at zero (`center=0`)

## Axes and labels

- [ ] Both axes have a label with **variable name and unit** (for example `Time (s)`, `Dose (μM)`)
- [ ] Tick label precision is sensible: no `1.0000` or `1.23456789`
- [ ] Log axes say so (for example `Dose (μM, log)`)
- [ ] The axis is not forced to start at zero unless zero is meaningful for the data
- [ ] No empty boxes in place of minus signs (`axes.unicode_minus`)

## Legends and panel labels

- [ ] The legend is **easy to read**; `frameon=False` removes the frame for a cleaner figure
- [ ] The legend does not cover data
- [ ] With more than five categories, consider direct labels (the name at the end of each line) instead of a legend
- [ ] Panel labels follow the journal: Nature lower-case bold `a`, `b`, `c`; Science and PNAS `A`, `B`, `C`; IEEE `(a)`, `(b)`, `(c)`
- [ ] Panel labels sit in the same place in every panel (top left is recommended, `transform=ax.transAxes` at `(-0.20, 1.05)`)
- [ ] Font size, colours and axis scales are **consistent** across the panels of a multi-panel figure

## Error bars and statistics

- [ ] Wherever there are error bars, shaded intervals or box plots, the **caption** states:
  - [ ] the error type (SD, SEM, 95% CI, IQR)
  - [ ] the sample size n
  - [ ] the significance test (t-test, Mann-Whitney, ANOVA, and any correction)
  - [ ] what the significance marks mean (`* p<0.05, ** p<0.01, *** p<0.001`)
- [ ] Significance marks do not cover data
- [ ] There are no "mean bars without error bars": reviewers will suspect there were no replicates

## Semantic compliance

Formal compliance is not semantic compliance. These eight items are the must-pass subset of scipilot's list of fifteen visualization pitfalls:

- [ ] **P1**: with fewer than 10 points per group, do **not** use mean bar charts; overlay a strip plot or use a box plot
- [ ] **P2**: no dual y-axes (unless both variables have the same unit)
- [ ] **P3**: no pie charts, no 3D bars, 3D pies or 3D surfaces
- [ ] **P4**: a sensible y-axis origin (proportions and probabilities start at zero; a truncated axis has a visible break mark)
- [ ] **P5**: every continuous colour scale has a colour bar, and the colour bar has a label and unit
- [ ] **P6**: when x is categorical, group means are **not** joined with lines
- [ ] **P12**: one figure makes one main point (split figures that argue several)
- [ ] **P14**: continuous values use viridis, magma or RdBu_r, **never** rainbow or jet

## Extra checks for figures with Chinese text

- [ ] A Chinese font is installed and used for the Chinese text
- [ ] In mixed text, Chinese uses the Chinese font while **numbers and variable names use Times New Roman**
- [ ] Minus signs render correctly, not as empty boxes (`axes.unicode_minus = False`)
- [ ] For Chinese journals, PDF is preferred over EPS (EPS handles Chinese TrueType fonts poorly)
- [ ] Captions and axis labels are in Chinese (unless the journal is in English)

## Final check

- [ ] Run:
  ```bash
  python scripts/check_figure.py figs/*.pdf figs/*.png \
         --min-dpi 300 --width-in 3.5 --height-in 2.625 --strict
  ```
  Only exit code 0 is a PASS.

- [ ] **Print** the PDF (or zoom to the paper's real size) and look at it: is the text big enough, are the lines clear, is the colour contrast enough?
- [ ] Check it once with a colour-blindness simulator (Color Oracle, Coblis)
- [ ] Show it to someone outside the field and see whether they get three things: what x is, what y is, and what distinguishes the lines or bars. If they cannot, the figure has failed to communicate.

---

## The whole checklist as commands

```bash
# 1. Make the figure (already done)
# 2. Final audit
python scripts/check_figure.py figs/*.pdf figs/*.png \
       --min-dpi 300 --width-in 3.5 --height-in 2.625 --strict

# 3. Final look by eye: open each file
```

Any FAIL: fix it, run again, until it passes.
