<!-- Translated from Chinese for Biorouter from Haojae/scipilot-figure-skill references/chart_selection.md (MIT, commit 43098ddb9e6a). Changes: translated to English; otherwise unchanged. See LICENSE-UPSTREAM. -->

# Choosing the chart type

Start every figure here: **decide what to show before deciding how to draw it**.

## Contents

- [Three decision axes](#three-decision-axes)
- [Data shape to chart type: quick table](#data-shape-to-chart-type-quick-table)
- [By data shape](#by-data-shape)
  - [1. One continuous variable: its distribution](#1-one-continuous-variable-its-distribution)
  - [2. One categorical variable: its proportions](#2-one-categorical-variable-its-proportions)
  - [3. One categorical and one continuous variable: comparing groups](#3-one-categorical-and-one-continuous-variable-comparing-groups)
  - [4. Two continuous variables: their relationship](#4-two-continuous-variables-their-relationship)
  - [5. Time series: the trend](#5-time-series-the-trend)
  - [6. Correlation among many variables](#6-correlation-among-many-variables)
  - [7. Matrix data](#7-matrix-data)
  - [8. Nested or crossed groups](#8-nested-or-crossed-groups)
- [Same data, different claims, different figures](#same-data-different-claims-different-figures)
- [When to split a figure](#when-to-split-a-figure)
- [Where chart types stop](#where-chart-types-stop)

---

## Three decision axes

Ask three questions before every figure.

### Axis 1: how many variables, of what type

| Combination | What it shows |
|---|---|
| 1 continuous | distribution |
| 1 categorical | proportions |
| 1 categorical + 1 continuous | comparison between groups |
| 2 continuous | relationship |
| 1 time + 1 continuous | trend |
| several continuous | correlation |
| a 2D matrix (n × m values) | pattern |
| nested groups (B within A, C within B) | hierarchy |

### Axis 2: what you want to say (the claim)

**This is the axis people forget.** The same data with a different claim needs a different figure.

- **Distribution**: "what this data looks like" → histogram, KDE, box plot
- **Comparison**: "A is higher, lower or different from B" → box plot, bar chart with error bars, violin
- **Relationship**: "the larger X, the larger Y" → scatter plus regression
- **Trend**: "change over time or dose" → line plus error band
- **Composition**: "how a total splits into parts" → stacked bars (**not a pie chart**)
- **Correlation**: "which variables go together" → correlation heat map, pair plot
- **Difference**: "is the difference between groups significant" → box plot with significance marks
- **Uncertainty**: "how precise is the estimate" → error bars, confidence band

### Axis 3: how much data

| Sample size | Advice |
|---|---|
| n ≥ 30 per group | box plots, bars with error bars and violins all work; the distribution is stable |
| 10 ≤ n < 30 per group | prefer box plots or violins; bars must show the raw points as a strip plot |
| 3 ≤ n < 10 per group | **strongly prefer** plotting the points (scatter or strip plot); use box plots with care (quartile estimates are unreliable) |
| n < 3 per group | **no box plots or violins**: the statistics mean nothing. Show every point |
| more than 10⁴ points in total | scatter with alpha 0.1 to 0.3 against overplotting, or use hexbin or a 2D KDE |

---

## Data shape to chart type: quick table

| Data shape | First choice | Alternative | Avoid |
|---|---|---|---|
| one continuous, distribution | KDE or histogram | box plot or violin | pie chart, line |
| one categorical, proportions | horizontal bars sorted by value | one stacked bar | **pie chart** (people judge angles poorly) |
| 1 categorical vs 1 continuous, n ≥ 10 per group | box plot plus strip plot | violin or bars with error bars | mean bars alone (they hide the distribution) |
| 1 categorical vs 1 continuous, n < 10 per group | strip plot or beeswarm | dot plot | box plot (unreliable), mean bars |
| 2 continuous | scatter plus regression line | 2D KDE or hexbin (large samples) | line (unless x is ordered) |
| time vs continuous | line plus error band | step plot, scatter | bars |
| several continuous (3 to 20 variables) | correlation heat map | pair plot | parallel coordinates (unless interactive) |
| many continuous (more than 20 variables) | heat map with clustering | PCA or UMAP scatter | a full-screen pair plot |
| matrix data | heat map (perceptually uniform colour map) | table | 3D surface |
| composition | stacked bars or treemap | 100% stacked bars | **pie chart**, **3D pie** |
| binary classifier performance | ROC or PR curve | confusion-matrix heat map | a bar of accuracy alone |

---

## By data shape

### 1. One continuous variable: its distribution

**First choice**: a KDE (kernel density estimate) for a smooth view of the shape; a histogram for small samples or discrete data.

**Alternatives**:
- **box plot**: quartiles, median and outliers
- **violin plot**: box plot and KDE combined
- **rug plot overlay**: a short tick per point along the bottom, so every point is visible when n is modest

**When not to**: with n < 5 every "distribution" plot is unreliable; list the points.

**Match the claim**:
- "the data are skewed left or right" → a KDE is clearest
- "where 75% of the samples fall" → a box plot is most direct
- "a few extreme outliers" → a box plot with outliers marked

### 2. One categorical variable: its proportions

**First choice**: horizontal bars sorted by value, with category names on the y axis.

**What is wrong with pie charts** (several journals refuse them):
- people judge angles at least three times worse than lengths
- with more than five categories there are not enough distinct colours
- 3D pies are a disaster: the perspective distorts every share

**Alternative**: a treemap (uses space well with more than ten categories)

### 3. One categorical and one continuous variable: comparing groups

**This is the most common figure in research. Decision tree**:

```
Sample size n per group?
├── n < 3          → list the points (dot plot); no statistical graphic
├── 3 ≤ n < 10     → strip plot, beeswarm or dot plot; use box plots with care
├── 10 ≤ n < 30    → box plot or violin with the strip plot overlaid (always)
└── n ≥ 30         → box plot, violin or bars with error bars
```

**Why overlay the raw points**:
- a mean bar draws n = 5 and n = 500 at the same height
- a box plot draws a bimodal and a unimodal distribution the same way
- overlaying the points shows the true distribution, and reviewers trust it at a glance

**Match the claim**:
- "A is significantly higher than B" → box plot with a significance bracket (* p < 0.05) and the test named in the caption
- "A and B overlap a lot" → violin plus strip plot, so the overlap is visible
- "A rises overall" → a line through the group means (only if the groups are ordered)

### 4. Two continuous variables: their relationship

**First choice**: scatter plot with a regression line and its 95% CI band

**More signals**:
- a third, categorical dimension → encode it twice, with `hue` (colour) and `style` (marker shape)
- a third, continuous dimension → a colour map (with a colour bar) or marker size
- **more than 1,000 points**: alpha 0.1 to 0.3 against overplotting, or hexbin or a 2D KDE

**When not to join points with lines**:
- x is categorical
- x is not continuous or ordered (an ID number, say)
- there is **no continuous relationship** between the points (a line suggests a trend that does not exist)

### 5. Time series: the trend

**First choice**: a line with an error band (SEM shading or 95% CI)

**When to join points**: when x is truly time or a sequence (dose, age band, any axis with continuous meaning)

**Several lines in one plot**:
- 2 to 3 lines: encode with colour and line style
- 4 to 6 lines: encode with colour and marker, and label each line at its end (no legend lookup)
- more than 6: split the figure, or use small multiples (one line per panel in a grid)

**Pitfalls**:
- do not draw a line between a pre-test and a post-test; a paired dot plot is more honest
- should the y axis start at zero? It depends on the size of the change and whether zero is a meaningful baseline

### 6. Correlation among many variables

**First choice**: a correlation heat map (n columns × n columns)

**Settings**:
- data with two meaningful directions (positive and negative) → diverging colour map `RdBu_r` with `center=0`
- annotate with the r values
- a large matrix (more than 20 columns) → reorder rows and columns by hierarchical clustering

**Alternative**: a scatter-plot matrix (pair plot), readable with 4 to 8 variables and a blur beyond that

### 7. Matrix data

Typical cases: gene expression matrices, confusion matrices, feature maps, similarity matrices.

**Choosing the colour map**:
- one-directional data (all positive) → `viridis`, `magma`, `inferno`, `cividis`
- two-directional data → `RdBu_r`, `PiYG`, `seismic` with `center=0`
- **never** `rainbow`, `jet` or `hsv`: they are not perceptually uniform

**Notes**:
- with few rows and columns, `annot=True` shows the numbers
- with many rows and columns in a sparse matrix, use `imshow`, turn off the grid, add a `colorbar`
- a confusion matrix normalised by row shows precision and recall

### 8. Nested or crossed groups

Example: 3 doses × 4 time points × 2 sexes × repeated measures of one response.

**Mapping**: assign each dimension to a visual channel.

| Mapping | Priority | Capacity |
|---|---|---|
| x axis | 1 | medium (5 to 10 categories) |
| colour | 2 | small (3 to 5) |
| marker or line style | 3 | very small (2 to 3) |
| panels (small multiples, facets) | 4 | medium (2 to 8 panels) |
| y axis | y is the response, not a grouping channel | — |

**Rule**: the number of dimensions must fit the product of the channels' capacities; otherwise **split the figure** (see below).

---

## Same data, different claims, different figures

### Example 1: the effect of drugs A and B on response time

Data: 30 subjects × 2 drugs × 5 time points = 300 measurements.

| Claim | Recommended figure | Why |
|---|---|---|
| "drug A is faster than B overall" | box plot (x = drug, y = time, all time points pooled) | flattening time focuses on the groups |
| "A and B diverge most at t = 3" | line (x = time, y = mean, hue = drug, with error bands) | shows the dynamics |
| "subjects differ a great deal" | spaghetti plot (a thin line per subject) with a thick mean line | makes the variability visible |
| "A and B differ significantly at t = 3" | paired box plot with a significance bracket, for t = 3 only | one comparison with its statistics |

**The same data, four entirely different figures.** Ask for the claim first.

### Example 2: a gene expression profile

Data: an expression matrix of 1,000 genes × 20 samples, the samples in two groups.

| Claim | Recommended figure |
|---|---|
| "the two groups separate" | PCA or UMAP scatter (hue = group) |
| "which genes are differentially expressed" | volcano plot (log2 FC against −log10 p) |
| "the genes of a pathway all go up" | heat map of the subset (rows = pathway genes, columns = samples) |
| "how similar the samples are overall" | sample-by-sample correlation heat map with clustering |

---

## When to split a figure

### When to split

Split when **any one** of these holds:

1. **More than 12 combinations of dimensions**: 4 × 4 = 16 panels fit on a page but readers cannot take them in
2. **Colliding x labels**: more than 8 categories on x, needing 45° or more of rotation to fit
3. **More than 6 legend entries**: beyond short-term memory, so readers keep looking back and forth
4. **A y scale spanning several orders of magnitude that cannot be logged**: plot the magnitudes separately
5. **Two things to say**: "A is faster than B" and "A is more accurate than B" are two figures

### How to split

- **by a grouping dimension**: a figure with hue = sex becomes fig 1 (male) and fig 2 (female)
- **by panel**: a 2 × 2 figure becomes fig 1 (a, b) and fig 2 (c, d)
- **by claim**: a figure that argues three things becomes three small figures
- **main figure and supplement**: the main figure carries the main result, the rest goes in the supplementary material

---

## Where chart types stop

### Line versus scatter

| | Line | Scatter |
|---|---|---|
| continuous relationship between points | **required** | not required |
| x is | time, dose, sequence | anything |
| suits | trends, dynamics | relationships, correlation |
| risk | **joining points that should not be joined**, suggesting a trend that does not exist | overplotting |

### Bars versus box plots

| | Bars (with error bars) | Box plot |
|---|---|---|
| shows | mean ± error | median, quartiles, outliers |
| assumes | unimodal, near Gaussian | nothing |
| suits n | ≥ 30 | ≥ 10 |
| a bimodal distribution | invisible, swallowed by the mean | also hard to see (but better than bars) |
| **best practice** | overlay a strip plot | overlay a strip plot |

**The core rule**: when n is small or the shape of the distribution is unknown, **default to box plots over bars**.

### Heat map versus scatter-plot matrix

| | Heat map | Scatter-plot matrix |
|---|---|---|
| information density | high | medium |
| shows | one statistic (r, expression value) | the full bivariate distribution |
| suits | 5 to 50+ columns | 2 to 8 columns |
| drawback | one statistic only | blurs with many dimensions |

Rule of thumb: more than 8 variables, use a heat map; 2 to 8, a pair plot shows more of the distribution.
