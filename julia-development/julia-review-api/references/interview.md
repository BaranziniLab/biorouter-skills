# Review interview: carry-over, GitHub issue, release strategy

## Prior-review carry-over

Before interviewing the user, check the project root for sibling plan files:
`DESIGN_REVIEW_PLAN.md`, `API_REVIEW_PLAN.md`, `INTEGRATION_REVIEW_PLAN.md`
(skipping this skill's own output). For each that exists, read its `Stated
values`, `Release strategy`, `Decisions`, and `Issue` metadata.

When asking the interview questions (stated values, GitHub issue, release
strategy), present prior answers and ask only for deltas — do not re-pose
questions the user has already answered in a sibling plan unless the framing
genuinely differs. If an `Issue` number is recorded, ask whether to reuse it or
open a new one.

Record carried-over answers verbatim. Do not paraphrase.

## GitHub issue

Ask: **"Would you like this review posted to GitHub? (a) open a new issue, (b) append it to an existing issue — give me the number, (c) no."**

- For (a), draft the title and body, show them to the user, and run
  `gh issue create` only after they approve the exact text. GitHub assigns the
  number; read it from the URL the command prints.
- For (b), use the number the user gave, and likewise get approval for the exact
  comment text before running `gh issue comment`.
- For (c), or if the repository has no GitHub remote or `gh` is unavailable,
  record `- **Issue**: n/a`.

Record the resulting number in the plan's Metadata as `- **Issue**: #NNN`.
Commits reference it in the body, never the subject; only the commit that
closes it says `Fixes #NNN`.

## Release strategy

If any approved item is breaking, ask whether to cut a final non-breaking
release first and whether to release between breaking clusters; `decide-later`
is acceptable, and the implementer asks at the relevant moment.
