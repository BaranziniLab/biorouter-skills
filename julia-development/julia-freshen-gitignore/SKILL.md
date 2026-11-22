---
name: julia-freshen-gitignore
description: "Bring a Julia package's .gitignore up to date (Manifest.toml, docs/build and the like). Use as the first step of julia-freshen-package or when a Julia repository's .gitignore is stale."
license: Apache-2.0 AND MIT
user-invocable: true
metadata:
  version: "1.0.0"
  origin: "adapted"
  upstream: "timholy/claude_config/skills/freshen-gitignore@225ce60094c1ecb823b3cb7abf2fd390185643ef"
  upstream_licence: "MIT"
---

<!-- Adapted for Biorouter from timholy/claude_config (skills/freshen-gitignore, commit 225ce60094c1), MIT. Changes: renamed with a julia- prefix; Claude Code paths, slash commands and subagent names replaced with Biorouter equivalents. See LICENSE-UPSTREAM. -->

Ensure the Julia package in the current directory has an appropriate `.gitignore`. The following must be covered, anywhere they appear:

- `*.jl.cov`, `*.jl.*.cov`, `*.jl.mem`
- `Manifest.toml` and `Manifest-v*.toml` (in root and in `docs/` if present)
- `docs/build/` if the package has Documenter docs

Check the existing `.gitignore` (if any) and add only what is missing. Do not remove existing entries.
