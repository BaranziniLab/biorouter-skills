---
name: ggplot-visualization
description: "The one ggplot2 style for R figures: theme, base size and font hierarchy, colourblind-safe palettes, point and line sizes, human labels, non-overlapping text, and export size and resolution, plus ggplot2 4.0 features and grammar-of-graphics technique. Apply whenever writing, modifying or reviewing ggplot2 plotting code in R, or making an R figure publication-ready."
license: Apache-2.0 AND MIT
user-invocable: false
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "Broccolito/ggplot-skills/SKILL_ggplot.md@7f430d5 (lab); jsperger/llm-r-skills/skills/ggplot2@7a10126fafd6d19b340da2661c7559b120264ffb; GPTomics/bioSkills/data-visualization/ggplot2-fundamentals@d91ed3d"
---

# ggplot2 Visualization Style

This is the one canonical R plotting style for Biorouter. It folds in the lab's fuller ggplot guide (Broccolito/ggplot-skills), a ggplot2 4.0 reference (jsperger/llm-r-skills, MIT) and the grammar-of-graphics technique from the Biomedical `data-visualization` bundle's former `ggplot2-fundamentals` component (GPTomics/bioSkills, MIT). Licences are in `LICENSE-UPSTREAM`.

**Precedence.** These rules win over any other plotting example, including the Biomedical bundles' R snippets and the reference files below. Assignment and pipes follow `r-scripting` (`=`, `|>`). When you quote an upstream example, keep it as written; when you write new code from it, write it in this style.

## Theme and type

- Use `theme_minimal(base_size = 14)` or `theme_classic(base_size = 14)`. Never `theme_gray()`.
- Remove minor grid lines (`panel.grid.minor = element_blank()`); keep major lines subtle or remove them.
- At most three type sizes. Hierarchy: title 16 to 18 pt, axis titles 12 to 14, axis text and legend 10 to 12, annotations 9 to 11.
- White background; legend at the top or right, never covering data.

## Colour

- Categorical: muted, colourblind-safe palettes: Okabe-Ito (`#E69F00 #56B4E9 #009E73 #F0E442 #0072B2 #D55E00 #CC79A7`), or RColorBrewer `Set2`, `Dark2`, `Pastel1`, `Pastel2`, `Set3`. Never the default hue palette, and never pure red, green and blue together.
- Continuous: `viridis`, `magma`, `plasma`, `inferno` or `cividis`.
- Diverging: `RdBu`, `RdYlBu`, `PuOr`, `BrBG` or `Spectral`, centred at a meaningful value (zero, the null, the reference group).
- Overlapping points get `alpha` (0.6 to 0.8).

## Marks

- Points: `size = 2.5` standard, 3.5 for sparse emphasis, 1.5 with `alpha = 0.6` for dense data.
- Lines: `linewidth = 0.8` standard (use `linewidth`, never `size`, for lines), 1.2 for fitted lines, 0.5 for connectors.
- Error bars: `linewidth = 0.6, width = 0.2`.
- Large scatters (over about 50,000 points) in a vector file: rasterise the point layer with `ggrastr::rasterise()`.

## Labels

- Natural language, never variable names: `log_fc` becomes "Log Fold Change", `Sepal.Length` becomes "Sepal Length".
- Units in parentheses: "Temperature (°C)". Title case for axis labels, sentence case for titles and captions.
- Text labels on points use `ggrepel::geom_text_repel()`, and raise `max.overlaps` (default 10) so labels are not silently dropped.
- Grouped bars, error bars and points share one `position_dodge(width = 0.8)`.

## Export

- Default: `ggsave("plot.png", p, width = 5, height = 4, dpi = 800)`.
- For a journal, size to the column and state the units: single column 89 mm (3.5 in), 1.5 column about 120 mm (5 in), double column 183 mm (7 in).
- Vector output: `ggsave("plot.pdf", p, width = 5, height = 4, device = cairo_pdf)` so fonts are embedded. TIFF for journals that ask: `dpi = 800, compression = "lzw"`.

## Code

- Programmatic aesthetics: `aes(x = .data[[var]])`, or `{{ var }}` inside a function. Never `aes_string()`.
- Build a project theme once as a function and reuse it:

```r
theme_publication = function(base_size = 14){
  theme_minimal(base_size = base_size) +
    theme(
      panel.grid.minor = element_blank(),
      panel.grid.major = element_line(color = "grey90", linewidth = 0.3),
      axis.line = element_line(color = "grey30", linewidth = 0.4),
      legend.position = "top",
      plot.margin = margin(10, 10, 10, 10)
    )
}
```

- ggplot2 4.0 and later: check `packageVersion("ggplot2")`. From 4.0, plot properties are S7 (`p@data`; `p$data` is deprecated), built-in themes take `ink`, `paper` and `accent` (`theme_minimal(base_size = 14, ink = "grey20")`), and `theme(geom = element_geom(...))` sets layer defaults; see `references/ggplot2-4-features.md`.

## Example

```r
library(ggplot2)

p = ggplot(data, aes(x = x_var, y = y_var, color = group)) +
  geom_point(size = 2.5, alpha = 0.8) +
  geom_line(linewidth = 0.8) +
  scale_color_brewer(palette = "Set2") +
  labs(x = "Dose (mg/kg)", y = "Response (AU)", color = "Group") +
  theme_minimal(base_size = 14) +
  theme(panel.grid.minor = element_blank(), plot.margin = margin(10, 10, 10, 10))

ggsave("plot.png", p, width = 5, height = 4, dpi = 800)
```

## Automatic corrections

When editing existing ggplot code, apply these fixes:

- `theme_gray()` or no theme → `theme_minimal(base_size = 14)`.
- `<-` → `=` in code you write or rewrite (see `r-scripting` for files in another consistent style).
- Missing colour scale → an appropriate `scale_color_*` or `scale_fill_*` from the lists above.
- `size =` on a line geom → `linewidth =`; `aes_string()` → `.data[[ ]]`.
- Missing or default dimensions → `width = 5, height = 4, dpi = 800`, or the journal column.
- Raw variable names in labels → human labels with units.

## Review checklist

Before delivering a figure, state for each line whether it holds:

- [ ] Text readable at print size; no more than three type sizes.
- [ ] Labels in natural language, with units.
- [ ] Palette colourblind-safe and muted; diverging palette centred.
- [ ] No label overlaps data or another label; legend placed well.
- [ ] Not `theme_gray()`; grid subtle or removed.
- [ ] Point and line sizes visible at the final size.
- [ ] Exported at the stated size and resolution, fonts embedded in vector output.

## Read on demand

- `references/publication-guide.md`: the lab's full guide, with templates for labelled scatter, bars with error bars, box plus points, and heatmaps, and the dependency list.
- `references/ggplot2-technique.md`: grammar in layers, scales, facets, tidy evaluation, ggtext labels, export devices and common failure modes.
- `references/ggplot2-4-features.md`: S7 property access, ink/paper/accent theme defaults, theme shortcuts, label dictionaries, discrete-scale and facet improvements in ggplot2 4.0.

## Related skills

- `python-visualization` is the matplotlib and seaborn counterpart; `figure-qa` checks a rendered figure; the Biomedical `data-visualization` bundle holds the omics-specific plot types (volcano, Manhattan, genome tracks, heatmaps) and defers to this skill for style.
- This skill replaces the `data-visualization` bundle's `ggplot2-fundamentals` component; a copy of that component still installed is an earlier version of `references/ggplot2-technique.md` and should yield to this skill.
