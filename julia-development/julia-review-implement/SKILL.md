---
name: julia-review-implement
description: "Implement a Julia review plan (API_REVIEW_PLAN.md and its siblings) chunk by chunk, with tests and deprecations, resuming from the plan's status after a break. Use after julia-review-api or when the user asks to carry out a review plan."
license: Apache-2.0 AND MIT
user-invocable: true
metadata:
  version: "1.0.0"
  origin: "adapted"
  upstream: "timholy/claude_config/skills/review-implement@225ce60094c1ecb823b3cb7abf2fd390185643ef"
  upstream_licence: "MIT"
---

<!-- Adapted for Biorouter from timholy/claude_config (skills/review-implement, commit 225ce60094c1), MIT. Changes: renamed with a julia- prefix; Claude Code paths, slash commands and subagent names replaced with Biorouter equivalents. See LICENSE-UPSTREAM. -->

# Review Implement

Use only when a review plan file exists in the project root.

## Step 1: Orient

Detect which plan file is present:

- `DESIGN_REVIEW_PLAN.md` → design review
- `API_REVIEW_PLAN.md` → API review
- `INTEGRATION_REVIEW_PLAN.md` → integration review

If more than one exists, ask which one to work on this session. If none exist, stop and
tell the user to run a review first (the julia-review-api skill, or a design or integration review).

Read `references/plan-file.md`, the plan, and the matching
SESSION file (`DESIGN_REVIEW_SESSION.md`, `API_REVIEW_SESSION.md`, or
`INTEGRATION_REVIEW_SESSION.md`) if present. `Stated values` breaks ties, and
`Release strategy` and `Decisions` are binding.

If every chunk is `complete` or `dropped`, point the user to the session ledger
for a summary. If the plan's Metadata contains an `Issue` entry that is not
`n/a`, remind the user to close that issue.

## Step 2: Pick the next chunk(s)

A chunk is ready when it is `not-started` and all its dependencies are
`complete`. Batch all ready `decide` chunks: they produce no diff, and answering
them up front unblocks downstream `implement` chunks.

Say which chunk you are taking, how you'll verify it, and any concerns, then
proceed. If the chunk is part of a cluster, name the cluster and how many
siblings remain.

After finishing a chunk, decide whether to stop for review or continue. Review
cost should scale with the risk of the change. A chunk whose diff is small and
mechanical (a rename, a one-line fix, a docstring edit, no behavior change)
does not justify a full stop: summarize it in a line, update its status, and
continue; when several such chunks accumulate, present them together for one
review and commit. A chunk that changes behavior, touches a public interface,
or required a judgment call gets a stop (Step 7); continue only if the user
says so. Always stop at `decide` chunks, on test failures or new ambiguities,
and at the end of the plan. Refresh the session handoff (Step 6) whenever you
stop, not after every chunk.

## Step 3: Implement, by chunk kind

### Kind: `preflight`

This is CHUNK-001 in every plan. It establishes the baseline before any change.

- Confirm working tree is clean (`git status`). If not, surface the issue and stop.
- Run the full test suite with `include("test/runtests.jl")` in the MCP Julia session.
- Run `Test.detect_ambiguities(MyPkg)` and record the count.
- Note the current `Project.toml` version.
- Record clean-tree status, test result, ambiguity count, and starting commit/version directly in this chunk's `Notes`. Mark the chunk `complete`. No commit.

### Kind: `decide`

The chunk encodes a question that needs an author's decision before implementation
can proceed.

- Quote the originating finding so the user has context.
- Pose the question. If you have a recommendation, give it briefly, grounded in
  `Stated values`.
- Capture the user's answer in the plan's `Decisions` section, tagged with the
  chunk ID, with enough rationale to reconstruct the choice later.
- Mark `complete`. No commit unless the answer demands an immediate doc edit.

### Kind: `investigate`

- Perform read-only research (grep, read files, MCP queries).
- Write findings into the chunk's `Notes` field.
- If the work suggests new chunks (e.g., "this affects 4 call sites, each its
  own implement chunk"), add them in dependency order with status `not-started`
  before closing.
- Mark `complete`. No commit unless the investigation produced an artifact under
  version control (rare).

### Kind: `implement`

1. Make the change.
2. If `Breaking: yes`:
   - Add a deprecation shim where appropriate (`Base.@deprecate` or a manual
     deprecation warning forwarding to the new signature).
   - Migrate all internal call-sites within the package (tests, docstrings,
     examples, internal callers).
3. Add the planned tests.
4. Run the full test suite with `include("test/runtests.jl")` in the MCP Julia
   session. Reserve `Pkg.test()` for the final check before a PR.
5. Run `Test.detect_ambiguities(MyPkg)` and compare against the baseline. Flag
   any new ambiguities; investigate before declaring the chunk complete.
6. Stage the changes for the user's review. Do not commit yourself.

### Kind: `version-bump`

Auto-appended whenever any `Breaking: yes` chunk exists. May be the only
version bump (single terminal release) or one of several (per-cluster releases),
depending on the recorded `Release strategy`.

- Verify every dependency (the breaking chunks it covers) is `complete` and that
  no covered cluster is half-finished.
- Update `Project.toml`: bump minor for 0.x with breaking changes; bump major
  for ≥1.x breaking changes; bump patch/minor for non-breaking improvement
  releases.
- Update `CHANGELOG.md` if one exists.
- Stage for the user's review.

### Kind: `release-baseline` / `release-breaking`

Coordination chunks that do not modify package source. Inserted by the planning
skill or mid-pipeline (per Step 5) when the user opts for a release at this
point.

- Confirm tests pass and the tree is clean.
- Walk the user through the release steps explicitly: bump `Project.toml`,
  commit, tag, request registration via `JuliaRegistrator` on the merge commit
  (or the user's preferred mechanism). Be explicit that the Julia registry is
  separate from git tags — registration is its own step.
- Do **not** perform the registration yourself. Releases are user actions.
- Mark `complete` once the user confirms the release has been requested.

## Step 4: Scope discipline

- Implement only the current chunk. If you notice related problems, record them
  in `Open Questions` rather than fixing in-flight.
- If the chunk turns out larger than expected, do the core and split the
  remainder into new chunks before closing.

## Step 5: Update the plan

After implementation:

1. Update `Status` to `complete` / `blocked` / `dropped` (one-line reason for the
   latter two).
2. Fill `Notes` with decisions, deviations, and anything the next session needs.
3. Add any new chunks discovered during work in dependency order.
4. Append one line to the session ledger at the bottom of the plan:

   > `- YYYY-MM-DD CHUNK-XXX (name) → next: CHUNK-YYY`

5. **Pre-breaking-release prompt** (only if `Release strategy` is `decide-later`
   and the next ready chunk is the first `Breaking: yes` chunk in the plan):
   ask whether to cut a final non-breaking release first; if yes, insert a
   `release-baseline` chunk before it and update `Release strategy`.
6. **Inter-cluster release prompt** (only if `Release strategy` is `decide-later`
   and multiple breaking clusters remain): ask whether to release between them
   or batch into one terminal breaking release; insert `release-breaking`
   chunks accordingly and update `Release strategy`.

## Step 6: Write the session handoff

Whenever you stop, write (overwriting) the session handoff matching the plan
kind (`DESIGN_REVIEW_SESSION.md`, `API_REVIEW_SESSION.md`, or
`INTEGRATION_REVIEW_SESSION.md`). It records only what the next session cannot
recover from the plan or `git status`:

```markdown
# Session Handoff — YYYY-MM-DD

## In progress
[CHUNK-XXX and what remains, or "none"]

## Shim choices
- ...

## Fragile assumptions and gotchas
- ...

## Test and ambiguity state
[only if changed from the preflight baseline: test result, ambiguity count and delta]
```

## Step 7: Stop for review

Tell the user:

1. What was done and how it was verified, in a line per chunk since the last
   stop.
2. What's next.
3. Any cluster left half-finished, and how many of its chunks remain.

Then invite a commit (`git add -p && git commit`) while you still have the
context to explain or revise the change. State lives in the plan and handoff
files, so julia-review-implement resumes equally well in this session or in a new chat.

If a cluster was just completed, add a one-line PR nudge (open a PR for the
cluster now, or hold for a terminal bundle). Skip on `decide` / `investigate`
chunks that produced no commit.

## Important notes

- Commit messages describe the change and its motivation; comments and
  docstrings follow `references/code-comments.md`. Neither cites chunk IDs or the
  plan file, which may be deleted.
- If `Stated values` would justify a different choice than the originating
  finding suggested, follow `Stated values` and record the divergence in
  `Notes`.
- If the user reports a regression after a chunk landed, treat it as a new
  chunk: write a failing test first (if reproducible without external data),
  add it to the plan, then fix.
