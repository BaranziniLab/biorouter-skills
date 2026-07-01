---
name: data-visualization-scientific-python
description: Create publication-quality scientific figures in Python with matplotlib, seaborn, plotly, and scientific schematics, including figure sizing, panel layout, color accessibility, export formats, and claim-to-figure consistency checks.
tool_type: python
primary_tool: matplotlib
user-invocable: false
license: Apache-2.0
---

# Scientific Python Visualization

Use this skill for Python figures that need to survive peer review, slides, or publication.

## Figure Contract

- Define the claim each figure supports.
- Choose plot type based on data structure and comparison.
- Set units, axis labels, scale, sample sizes, and uncertainty display.
- Use colorblind-safe palettes and direct labels where possible.
- Export vector formats for line art and high-resolution raster for heatmaps/images.

## Checks

- No hidden truncation or misleading axis limits.
- Summary plots show uncertainty and sample size.
- Multi-panel labels match text references.
- Captions describe methods and statistical test where needed.
- Figure values match the source table or script.

## Python Defaults

- Use `matplotlib` for controlled publication output.
- Use `seaborn` for statistical plots with careful theme overrides.
- Use `plotly` for interactive exploration, not final print figures unless requested.

## Related Skills

- `ggplot-visualization`
- `data-visualization/multipanel-figures`
- `claim-evidence-integrity`
