---
name: julia-freshen-package
description: "Orchestrate a full Julia package freshening, one step at a time with the user's approval: .gitignore, deprecations, Aqua.jl, ExplicitImports.jl, an API review and its implementation, generic indexing, coverage, docstrings and documentation. Use when the user asks to modernize, clean up or freshen a Julia package."
license: Apache-2.0 AND MIT
user-invocable: true
metadata:
  version: "1.0.0"
  origin: "adapted"
  upstream: "timholy/claude_config/skills/freshen-package@225ce60094c1ecb823b3cb7abf2fd390185643ef"
  upstream_licence: "MIT"
---

<!-- Adapted for Biorouter from timholy/claude_config (skills/freshen-package, commit 225ce60094c1), MIT. Changes: renamed with a julia- prefix; Claude Code paths, slash commands and subagent names replaced with Biorouter equivalents. See LICENSE-UPSTREAM. -->

Walk through the following package maintenance steps for the Julia package in the current directory. The package module name is determined by reading `Project.toml`.

Progress is kept in `.biorouter/freshen-package-status`, one `STATUS: step title` line per step below, in order (STATUS ∈ TODO/Optional/DONE, matching the headers). Create it if missing.

Perform the next step whose status is not DONE. If it is Optional, ask the user for their intent, moving to the next if it is declined.

After completing a step:

- mark it "DONE" in `.biorouter/freshen-package-status`
- if there are unmerged changes, propose a commit message and ask whether a commit should be made
- if no steps remain, inform the user about the current status and ask permission to delete `.biorouter/freshen-package-status`
- otherwise continue to the next step in this session. Stop and suggest starting a new chat and running the julia-freshen-package skill again only before one of the three reviews, which should start from fresh context: a review started in the session that just edited the code tends to accept those edits instead of judging them. `.biorouter/freshen-package-status` carries progress between sessions.

The ordering rationale: cheap deterministic cleanup runs first to clear the deck and to handle the things the reviews would otherwise duplicate (Aqua, ExplicitImports). The three reviews then run on cleaned-up code while the user's attention is fresh — these are the highest-judgment steps. API-dependent finishing work (generic-indexing tests, coverage, docstrings, docs) runs after the reviews so it targets the settled API; generic-indexing tests come first in that group so their `src/` fixes and new tests are in place before coverage measures them. Runic formatting is last so the substantive modernization can be bundled into a small number of PRs without being interrupted by the runic step's forced merge to the default branch.

Each review writes a plan that the julia-review-implement skill consumes. Mark the review DONE only after that plan is fully implemented, because the later steps assume the API is settled. Review plan and session files (`*_REVIEW_PLAN.md`, `*_SESSION.md`) go in `.git/info/exclude`, not in commits.

---

### TODO: update .gitignore
Use the julia-freshen-gitignore skill.

---

### TODO: remove deprecations

Search for `@deprecate` and `Base.depwarn` in `src/`.

For each deprecated operation found:
- Remove the deprecation
- Migrate or remove any associated tests (remove if the test's sole purpose was to verify the deprecated syntax and the new functionality is already fully covered; otherwise migrate to test the replacement)
- Update callers within the package if any

This step runs *before* the reviews because julia-review-implement may add new deprecation shims for breaking changes; those should remain in place for the current release cycle and be removed by the *next* freshening pass.

---

### TODO: add Aqua.jl
Use the julia-freshen-aqua skill.

---

### TODO: add ExplicitImports.jl
Use the julia-freshen-explicit-imports skill.

---

### Optional: limit struct mutability
Not part of this bundle. Look for `mutable struct` types whose fields are never reassigned after construction and propose making them immutable; ask before changing a public type.

---

### Optional: design review

Not part of this bundle. If the user wants one, review the package's overall design (module structure, abstractions, extension points) and write the findings as a plan in the format of julia-review-api's `references/plan-file.md`, so julia-review-implement can carry it out.

---

### Optional: API review

Use the julia-review-api skill.

---

### Optional: integration review

Not part of this bundle. If the user wants one, check how the package's pieces fit the Julia ecosystem (interfaces it should implement, such as iteration, indexing, broadcasting and `show`) and write the findings as a plan in the same format.

---

### TODO: enforce generic indexing
Use the julia-freshen-generic-axes skill.

---

### TODO: improve test coverage
Use the julia-freshen-coverage skill.

---

### TODO: add and improve docstrings
Use the julia-freshen-docstrings skill.

---

### TODO: add or improve documentation
Use the julia-freshen-docs skill.

---

### Optional: format with runic
Not part of this bundle. If the user wants it, format the package with Runic.jl (`runic --inplace .`) in its own pull request, after the substantive changes, and add a CI check for it. This step requires a PR to merge before continuing. Pause and wait for the user to confirm the merge.
