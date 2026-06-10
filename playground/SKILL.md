---
name: playground
description: Creates interactive HTML playgrounds — self-contained single-file explorers that let users configure something visually through controls, see a live preview, and copy out a prompt. Use when the user asks to make a playground, explorer, or interactive tool for a topic.
user-invocable: true
---

<!-- Adapted for BioRouter from anthropics/claude-plugins-official/plugins/playground (Apache License 2.0). -->

# Playground Builder

A playground is a self-contained HTML file with interactive controls on one side, a live preview on the other, and a prompt output at the bottom with a copy button. The user adjusts controls, explores visually, then copies the generated prompt back into BioRouter.

Use this when the user asks for an interactive playground, explorer, or visual tool for a topic — especially when the input space is large, visual, or structural and hard to express as plain text.

## How to build one

1. **Identify the playground type** from the user's request (see the six types below).
2. **Follow the matching layout and control guidance** for that type. If the topic doesn't fit any type cleanly, use the closest one and adapt.
3. **Write a single self-contained HTML file** that meets all core requirements below.
4. **Open it.** After writing the file, run `open <filename>.html` to launch it in the user's default browser.

## Core requirements (every playground)

- **Single HTML file.** Inline all CSS and JS. No external dependencies — no CDNs. If a CDN is down, the playground is dead, so ship everything in the file.
- **Live preview.** Updates instantly on every control change. No "Apply" button.
- **Prompt output.** Natural language, not a value dump. Mentions only non-default choices. Includes enough context to act on without seeing the playground. Updates live.
- **Copy button.** Clipboard copy with brief "Copied!" feedback that reverts after a moment.
- **Sensible defaults + presets.** Looks good on first load. Include 3–5 named presets that snap all controls to a cohesive combination.
- **Dark theme.** System font for UI, monospace for code/values. Minimal chrome.

## State management pattern

Keep a single state object. Every control writes to it, every render reads from it.

```javascript
const DEFAULTS = { /* the baseline values */ };
const state = { ...DEFAULTS };

function updateAll() {
  renderPreview(); // update the visual
  updatePrompt();  // rebuild the prompt text
}
// Every control calls updateAll() on change. Presets overwrite state then call updateAll().
```

## Prompt output pattern (`updatePrompt`)

```javascript
function updatePrompt() {
  const parts = [];

  // Only mention non-default values
  if (state.borderRadius !== DEFAULTS.borderRadius) {
    parts.push(`border-radius of ${state.borderRadius}px`);
  }

  // Use qualitative language alongside numbers
  if (state.shadowBlur > 16) parts.push('a pronounced shadow');
  else if (state.shadowBlur > 0) parts.push('a subtle shadow');

  prompt.textContent = parts.length
    ? `Update the card to use ${parts.join(', ')}.`
    : 'No changes from the defaults.';
}
```

## Copy button pattern

```javascript
copyBtn.addEventListener('click', async () => {
  await navigator.clipboard.writeText(prompt.textContent);
  const original = copyBtn.textContent;
  copyBtn.textContent = 'Copied!';
  setTimeout(() => { copyBtn.textContent = original; }, 1200);
});
```

## The six playground types

Each type has a one-line purpose and an ASCII layout hint. The two-panel split (controls left, preview right, prompt at bottom) is the default; the canvas/diagram types differ as noted.

**1. design-playground** — Visual design decisions: components, layouts, spacing, color, typography, animation, responsive behavior. Controls grouped by Spacing / Color / Typography / Shadow-Border / Interaction; preview applies state values directly to a preview element's inline styles. Use sliders for sizes/spacing/radius, toggles for on/off features, dropdowns for sets, HSL sliders for colors, clickable cards for layout structure, a viewport-width slider for responsive behavior.

```
+-----------+----------------+
| controls  | live component |
| by group  | preview        |
|           +----------------+
|           | prompt [Copy]  |
+-----------+----------------+
```

**2. data-explorer** — Data/query building: SQL builders, API designers, regex builders, pipelines, cron schedules. Controls grouped by Source/tables / Columns / Filters / Grouping / Ordering / Limits; render syntax-highlighted output with `<span>` color classes. Use clickable chips for selecting items, add-row buttons for filter/condition rows, dropdowns per row for join/aggregation, sliders for limit/offset.

```
+-----------+----------------+
| query     | syntax-hi'd    |
| controls  | code / diagram |
|           +----------------+
|           | prompt [Copy]  |
+-----------+----------------+
```

**3. concept-map** — Learning/exploration: concept maps, knowledge-gap identification, scope mapping, task decomposition with dependencies. Canvas-based — the interactive visual IS the control; users drag nodes and draw edges. Sidebar supplements with knowledge-level cycling, connection-type selector, node list, and actions (auto-layout, clear edges, reset). Use `<canvas>` with manual draws, hit-testing on mousedown/move, click-A-then-B edge drawing, hover tooltips.

```
+--------------------------------+
| canvas (drag nodes, draw edges)|
+-------------------+------------+
| sidebar controls  | prompt[Cp] |
+-------------------+------------+
```

**4. document-critique** — Document review: SKILL.md, READMEs, specs, proposals — any text needing approve/reject/comment feedback. Left: document with line numbers and colored left-border highlights (pending amber, approved green, rejected dimmed red). Right: filterable suggestions panel (All/Pending/Approved/Rejected) with per-card Approve/Reject/Comment and an optional comment textarea. Prompt generates only from approved suggestions and user comments.

```
+---------------+----------------+
| document w/   | suggestions    |
| line numbers  | filterable list|
+---------------+----------------+
| prompt (approved + comments)[Cp]|
+--------------------------------+
```

**5. diff-review** — Code review: git commits, PRs, diffs with line-by-line commenting. Left: commit header (hash, message, author/date). Right: diff content with hunks, line numbers, +/- indicators. Click any diff line to open a comment textarea; commented lines get a badge. Prompt output panel (fixed bottom-right) shows all comments formatted for review feedback, with Copy All.

```
+--------+-------------------------+
| commit | diff (files / hunks)    |
| header | +/- lines, click to add |
+--------+-------------------------+
| prompt output (all comments)[Cp] |
+----------------------------------+
```

**6. code-map** — Codebase architecture: component relationships, data flow, layer diagrams. Left: controls — view presets (Full System, Chat Flow, Data Flow, etc.), layer toggles (checkboxes), connection-type filters (color-coded checkboxes), and a list of user comments with delete buttons. Right: `<svg>` canvas with rounded-rectangle nodes and curved bezier connections (arrow markers, colored by type), zoom +/-/reset, legend bottom-left. Click a component to comment; comments feed the prompt.

```
+-----------+-------------------------+
| controls  | SVG nodes + connections |
| + comments| zoom, legend            |
|           +-------------------------+
|           | prompt [Copy]           |
+-----------+-------------------------+
```

## Common mistakes to avoid

- Prompt output is just a value dump → write it as a natural instruction.
- Too many controls at once → group by concern, hide advanced ones in a collapsible section.
- Preview doesn't update instantly → every control change must trigger immediate re-render.
- No defaults or presets → starts empty or broken on load.
- External dependencies → inline everything; a missing CDN must never break the file.
- Prompt lacks context → include enough that it's actionable without the playground open.
