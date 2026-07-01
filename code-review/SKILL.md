---
name: code-review
description: Review a pull request through a multi-stage, confidence-scored pipeline and post a single PR comment with only high-confidence findings. Use when asked to review a PR, or to review the local working-tree/branch diff when no PR exists.
license: Apache-2.0
user-invocable: true
---

<!-- Adapted for BioRouter from anthropics/claude-plugins-official/plugins/code-review (Apache License 2.0). -->

# Code review

Review a pull request and post one focused comment containing only high-confidence
issues. Run shell commands through the Developer extension. Requires the `gh` CLI,
authenticated. Make a todo list first, then work through the stages below in order.

If there is no PR (you are reviewing a local working tree or branch), skip the `gh`
steps: gather the diff with `git diff` (or `git diff <base>...HEAD`), run the same
review passes, apply the same scoring, and PRINT the surviving findings instead of
posting a comment.

## Stage 1 — Eligibility

Check the PR with `gh pr view <num> --json state,isDraft,author,title,comments,reviews`.
Do NOT proceed if any of these hold:
- The PR is closed or already merged.
- The PR is a draft.
- The change is trivial/obviously fine, or is an automated PR (bots, dependency bumps).
- You have already left a code review comment on this PR.

If ineligible, stop and say so. Re-run this check at the very end before posting (a PR
may have closed or merged while you worked).

## Stage 2 — Collect CLAUDE.md paths

Gather the file PATHS (not contents) of relevant CLAUDE.md files: the repo-root
CLAUDE.md if present, plus any CLAUDE.md in directories the PR touches. Keep this list
to cite later. CLAUDE.md is guidance for writing code, so not every instruction applies
during review.

## Stage 3 — Summarize the change set

Run `gh pr diff <num>` and `gh pr view <num>` and write a short summary of what the PR
changes. This grounds the review passes.

## Stage 4 — Parallel review passes

Use BioRouter subagents to run these passes IN PARALLEL — ask for several independent
subagents, one per pass. Each returns a list of candidate issues with the reason each
was flagged. Keep passes independent (no shared conclusions):

- **(a) Convention compliance.** Check the changes against the collected CLAUDE.md
  files and project house style. Only flag what CLAUDE.md actually calls out.
- **(b) Shallow bug scan.** Read ONLY the diff. Scan for obvious, large bugs. Do not
  pull in extra context. Skip nitpicks and likely false positives.
- **(c) Git history/blame.** Read `git blame` and history of the modified lines to
  surface bugs that only make sense in historical context.
- **(d) Prior PRs.** Find earlier PRs that touched these files (`gh pr list`, `gh search`)
  and check whether review comments on them apply to this change too.
- **(e) In-code comment guidance.** Read comments in the modified files and confirm the
  changes comply with any guidance written there.

For language-specific judgment, defer to the sibling skills `python-scripting` and
`r-scripting`; for biology code, `bio-skills`.

## Stage 5 — Confidence scoring

For every candidate issue, assign a 0–100 confidence score. For CLAUDE.md-flagged
issues, double-check the CLAUDE.md actually names that issue. Use this rubric verbatim:

- **0** — Not confident at all. A false positive that fails light scrutiny, or a
  pre-existing/unmodified issue.
- **25** — Somewhat confident. Might be real, might be a false positive; not verified.
  If stylistic, it is NOT explicitly called out in the relevant CLAUDE.md.
- **50** — Moderately confident. Verified real, but minor — a nitpick or rare in
  practice; not important relative to the rest of the PR.
- **75** — Highly confident. Double-checked and very likely real and hit in practice;
  the PR's approach is insufficient, OR it is directly mentioned in the relevant
  CLAUDE.md.
- **100** — Absolutely certain. Confirmed a definite bug that will happen frequently;
  evidence directly confirms it, introduced by this PR.

## Stage 6 — Filter

Drop every issue scoring below 80. If none remain, stop WITHOUT commenting (for a local
diff, report "no high-confidence issues").

## Stage 7 — Post the comment

Re-run the Stage 1 eligibility check. If still eligible, post ONE comment with
`gh pr comment <num> --body "..."`. Keep it brief, no emojis except the feedback prompt.
Cite each issue with a permalink using the FULL commit SHA (not a bash substitution —
the comment renders as Markdown) and an `L<start>-L<end>` line range with at least one
line of context above and below.

Permalink format (exact, or the Markdown preview breaks):
`https://github.com/<owner>/<repo>/blob/<full-sha>/<path>#L<start>-L<end>`

Comment format:

```
### Code review

Found N issues:

1. <brief description> (CLAUDE.md says "<...>")

<permalink with full sha + line range>

2. <brief description> (bug due to <file/snippet>)

<permalink>

<sub>- If this code review was useful, please react with 👍. Otherwise, react with 👎.</sub>
```

If somehow you reach this stage with zero issues, post `### Code review` / "No issues
found. Checked for bugs and CLAUDE.md compliance."

## False positives — always exclude

- Pre-existing issues, or issues on lines the PR did not modify.
- Anything a linter, typechecker, or compiler would catch (imports, type errors, broken
  tests, formatting, style newlines). Assume CI runs these separately.
- Pure nitpicks or style a senior engineer wouldn't flag.
- Changes that are likely intentional or part of the broader change.
- Issues silenced in code (e.g. a lint-ignore comment).
- General code-quality gripes (test coverage, docs) unless CLAUDE.md requires them.

## Hard rules

- Do NOT build, typecheck, or run the project. Those run separately in CI.
- Use `gh` for all GitHub interaction, not web fetch.
- You MUST cite and link every issue, including a link to any CLAUDE.md you reference.
