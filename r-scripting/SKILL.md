---
name: r-scripting
description: "R house style: = for assignment, the native pipe |>, no space before parentheses, minimal comments, and precedence over upstream R examples; routes package-building and performance work to their own skills. Apply whenever writing, editing or reviewing R code."
license: Apache-2.0
user-invocable: false
metadata:
  version: "1.1.0"
  origin: lab
  upstream: "none (lab-original)"
---

# R Scripting Conventions

Always follow these rules when writing any R code:

## Precedence over upstream examples

These conventions are the house style for new code and for code you edit. Many bundled examples, including every Biomedical bundle's R snippets and the Posit tidyverse style guide, use `<-` and `%>%`. When you write new code from such an example, write it in the house style below. When you quote an upstream example, or edit a file that already follows another style consistently, keep that file's style rather than mixing the two in one file.

## Assignment

Always use `=` instead of `<-` for all assignments — variables, function results, intermediate objects, everything.

```r
data = read.csv("data.csv")
result = lm(y ~ x, data = df)
```

## Piping

Always use the native pipe `|>` instead of `%>%` whenever possible.

```r
df |> filter(x > 0) |> summarise(mean_y = mean(y))
```

## Spacing around function calls and control flow

Do not add a space before `(` in function calls, function definitions, or control flow keywords:

```r
# correct
function(){

}

if(condition){

}

for(i in seq){

}

mean(x)
```

```r
# wrong
function () { }
if (condition) { }
for (i in seq) { }
mean (x)
```

## Comments

- Keep comments minimal — one short inline comment at most per logical block
- Only add a comment if the logic is genuinely non-obvious; omit otherwise
- Do not write block comments or multi-line comment headers

## Where other R work goes

- Building, testing, documenting or releasing an R package (`DESCRIPTION`, roxygen2, testthat, `R CMD check`, CRAN): load `r-package-development`.
- Making R code faster or lighter on memory (profiling, vectorisation, data.table, parallel work): load `high-performance-r`.
- Plotting with ggplot2: load `ggplot-visualization`, which owns the plotting style.
- Running code in the person's live R session: use the GptrAgent extension when it is installed.
