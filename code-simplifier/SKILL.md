---
name: code-simplifier
description: Simplify and refine recently-modified code for clarity, consistency, and maintainability while preserving exact functionality. Use after writing or editing code, or when asked to clean up / simplify a change.
user-invocable: true
---

<!-- Adapted for BioRouter from anthropics/claude-plugins-official/plugins/code-simplifier (Apache License 2.0). -->

# Code simplifier

Refine code so it is clearer, more consistent, and easier to maintain — without
changing what it does. Favor readable, explicit code over clever, compact code. This is
a balance: simpler, not terser.

## Scope

By default, only touch code that was recently modified in this session. Do not refactor
the whole file or unrelated code unless explicitly told to widen the scope. Identify the
changed regions first (e.g. `git diff`), then work within them.

## Preserve functionality — non-negotiable

Change only HOW the code does its job, never WHAT it does. All outputs, side effects,
public APIs, and observable behavior must stay identical. If a "simplification" would
alter behavior, do not make it.

## Apply project standards

Read CLAUDE.md and follow the project's house style and naming conventions. For
language-specific idioms, defer to the sibling skills rather than baking in rules:
- Python → `python-scripting`
- R → `r-scripting`
- biology-domain code → `bio-skills`

## General principles

- Remove needless complexity and nesting; eliminate redundant code and dead
  abstractions — but do not over-abstract or merge unrelated concerns.
- Prefer clear control flow over clever one-liners. Avoid dense, packed expressions.
- Avoid nested ternaries; use `if`/`else` chains or a dispatch table / match for
  multiple conditions.
- Keep names meaningful and consistent.
- Drop comments that merely restate obvious code; keep comments that explain *why*.
- Do not change public behavior, signatures, or APIs.
- Choose clarity over brevity. Fewer lines is not the goal; easier to read, debug, and
  extend is.

## Process

1. Find the recently changed code.
2. Spot opportunities to improve clarity and consistency.
3. Apply project standards and the principles above.
4. Confirm functionality is unchanged.
5. Show the change and explain it briefly.

## Output

For each change, show a before/after diff and a one-line reason. Example (Python):

Before:
```python
def label(x):
    return "hi" if x > 10 else ("mid" if x > 5 else "lo")
```
After:
```python
def label(x):
    if x > 10:
        return "hi"
    if x > 5:
        return "mid"
    return "lo"
```
Reason: replaced a nested ternary with a flat if-chain — same result, easier to read.

Example (shell):

Before:
```bash
if [ "$(wc -l < "$f")" -gt 0 ]; then echo nonempty; fi
```
After:
```bash
if [ -s "$f" ]; then echo nonempty; fi
```
Reason: used the built-in `-s` test instead of counting lines — same check, clearer.

Keep edits small and reviewable. If you find nothing worth simplifying, say so rather
than inventing churn.
