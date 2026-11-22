---
name: julia-freshen-docs
description: "Review and improve a Julia package's Documenter manual so it describes the package as it is now. Use when freshening a package or when the user asks to improve its documentation."
license: Apache-2.0 AND MIT
user-invocable: true
metadata:
  version: "1.0.0"
  origin: "adapted"
  upstream: "timholy/claude_config/skills/freshen-docs@225ce60094c1ecb823b3cb7abf2fd390185643ef"
  upstream_licence: "MIT"
---

<!-- Adapted for Biorouter from timholy/claude_config (skills/freshen-docs, commit 225ce60094c1), MIT. Changes: renamed with a julia- prefix; Claude Code paths, slash commands and subagent names replaced with Biorouter equivalents. See LICENSE-UPSTREAM. -->

Inspect the current state of documentation (README and/or `docs/`):
- For simple packages, the README may suffice. Even for packages that use `docs/`, the README should briefly summarize the package's purpose and scope.
- For complex packages, suggest a Documenter.jl `docs/` structure if not present.

The README badges should include CI status, documentation, coverage, and current version (check for missing or stale badges).

Whether via README or `docs/`, the documentation should include:
- installation instructions, especially if it's more than `Pkg.add("<pkgname>")`
- at least one usage example for the most important features of the package
- if the package concepts are non-obvious, a section that explains them to users
- if using `docs/`, a reference section describing the package's API

Note: docstring coverage on exported and public symbols is handled by the julia-freshen-docstrings skill, not this one.

Summarize findings and suggestions for the user. **[pause for approval]** Then implement. Documentation prose, like code comments, should describe the package as it is now, not its development history or planning (`references/code-comments.md`).

Code examples in documentation should use `jldoctest` blocks where feasible so they are verified during CI. `jldoctest` output must match exactly, so ensure it is deterministic: use fixed inputs rather than `rand()`, and watch for unordered collections (`Dict`, `Set`), platform-sensitive numeric formatting, or object addresses in `show` output — restructure the assertion (e.g., sort and collect an unordered result) to avoid fragility. Examples with expensive setup, side effects, or inherently non-deterministic output are acceptable exceptions.

Unless instructed otherwise, any untested examples (README or untested `/docs` examples) should be tested via MCP to be certain they work. You may take it for granted that the user has issued `using PkgName` prior to running the example. Other setup, module-qualification, etc., should be spelled out.

If adding or updating Documenter docs:
- Update the CI YAML to build and deploy documentation
- If the repo is private, ensure the `DOCUMENTER_KEY` secret is passed to `julia-docdeploy` (the modern `julia-docdeploy` action handles SSH setup internally when given this secret — no manual SSH key steps are needed)
- Ensure `docs/Project.toml` has `[compat]` bounds for Documenter and any other dependency listed there (other than the package itself)
- In `docs/make.jl`, verify `makedocs` includes `modules=[PkgName]` and `checkdocs=:exports` (or `:all`); omitting these lets undocumented exports slip through silently
