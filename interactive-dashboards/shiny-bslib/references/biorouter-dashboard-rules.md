<!-- From the lab's gptr package, inst/gptr/skills/shiny-bslib (Apache-2.0), commit 0280d953ee42: the layout
and accessibility rules for dashboards, without gptr's artifact commands. -->

# Dashboard rules used across Biorouter

These are the rules the lab applies to every Shiny dashboard, from gptr's in-session apps. They
sit on top of the bslib guidance in this skill.

- One file ending in `shinyApp(ui, server)`. Do not call `setwd()` or `install.packages()` inside an app.
- Start dashboards with `page_sidebar(sidebar = sidebar(...), fillable = FALSE, ...)`.
  Set `fillable = FALSE` explicitly so the main area can shrink beside an open sidebar;
  bslib's filling layout otherwise imposes a desktop minimum width. Keep inputs in the named
  `sidebar`; compact KPIs as `value_box()` in
  `layout_columns(..., fill = FALSE)`;
  each chart or table in `card(card_header(), ..., full_screen = TRUE)`; never nest cards or pages.
- Keep plots readable at narrow widths with a bounded height (for example,
  `plotOutput(..., height = "300px")`) and legible axis text. Wrap wide tables in a standard
  `table-responsive` div with `tabindex = 0`, `role = "region"` and a descriptive `aria-label`
  so keyboard users can scroll horizontally.
- Stack chart and table cards when a sidebar leaves little content width; check each card
  against the visible content area at 320, 768 and 1440 pixels and at 200% browser zoom.
  Page scroll width alone can miss a clipped sidebar main area.
- Prefer `numericInput()` for exact numeric thresholds when keyboard focus must preserve the
  value; use sliders for visual adjustments.
- `renderPlot()` with ggplot2 and `theme_minimal()`; plotly, DT or leaflet only if they are
  installed. Filter once in `reactive()`; `req()` for empty inputs, `validate(need())` for empty
  results; no custom CSS or JS. Use `=` for assignment and `|>` for data transforms;
  add ggplot2 geoms, labels, scales and themes with `+`.

In this example `markers` is a data frame the app already has.

```r
library(shiny)
library(bslib)
ui = page_sidebar(
  title = "Markers",
  fillable = FALSE,
  sidebar = sidebar(textInput("gene", "Gene")),
  layout_columns(value_box("Markers shown", textOutput("n")), fill = FALSE),
  card(
    card_header("Top markers"),
    div(
      class = "table-responsive", tabindex = 0, role = "region",
      `aria-label` = "Top markers", tableOutput("top")
    ),
    full_screen = TRUE
  )
)
server = function(input, output, session) {
  shown = reactive(markers[grepl(input$gene, markers$gene, ignore.case = TRUE), ])
  output$n = renderText(nrow(shown()))
  output$top = renderTable({
    validate(need(nrow(shown()) > 0, "No marker matches the search."))
    head(shown(), 20)
  })
}
shinyApp(ui, server)
```
