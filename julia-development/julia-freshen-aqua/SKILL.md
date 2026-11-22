---
name: julia-freshen-aqua
description: "Add Aqua.jl quality checks to a Julia package's tests and fix what they report (ambiguities, unbound type parameters, stale dependencies, piracy, compat bounds). Use when freshening a package or when the user asks for Aqua."
license: Apache-2.0 AND MIT
user-invocable: true
metadata:
  version: "1.0.0"
  origin: "adapted"
  upstream: "timholy/claude_config/skills/freshen-aqua@225ce60094c1ecb823b3cb7abf2fd390185643ef"
  upstream_licence: "MIT"
---

<!-- Adapted for Biorouter from timholy/claude_config (skills/freshen-aqua, commit 225ce60094c1), MIT. Changes: renamed with a julia- prefix; Claude Code paths, slash commands and subagent names replaced with Biorouter equivalents. See LICENSE-UPSTREAM. -->

## 1. Add Aqua.jl as a test dependency

Check how test dependencies are currently specified in this project:

- **If `test/Project.toml` exists**, add Aqua via:
  ```
  julia --project=test -e 'using Pkg; Pkg.add("Aqua")'
  ```
  and update the `[compat]` section of `test/Project.toml`.

- **If the root `Project.toml` uses `[extras]`/`[targets]`**, check the Julia compat lower bound:
  - **Julia 1.11+**: `julia --project -e 'using Pkg; Pkg.add("Aqua"; target=:extras)'`
  - **Julia 1.10**: `julia --project -e 'using Pkg; Pkg.add("Aqua")'`, then manually move the Aqua entry from `[deps]` to `[extras]` and add `"Aqua"` to the `test` list under `[targets]`.

  In either case, add a version bound under `[compat]` with a lower bound compatible with Julia 1.10 (LTS).

## 2. Run Aqua checks

Run:

```julia
using TestEnv
TestEnv.activate()
using <PackageModule>, Aqua
Aqua.test_all(<PackageModule>)
```

where `<PackageModule>` is the name of the package defined in this repository.

Run this on Julia versions that include the user's default version and any
others tested on CI. Supported versions can be determined from `Project.toml`
and the relevant GitHub workflow (if present). Several `Aqua.test_all` checks —
notably `test_ambiguities` and `test_unbound_args` — depend on method tables and
ambiguity resolution that change across Julia versions, so a check can pass on
one version and fail on another. Neither version is uniformly stricter.

## 3. Report and fix

Summarize the results for the user. Propose fixes for any failures. Wait for user approval before making changes.

## 4. Add to test suite and verify

Once all Aqua checks pass, add `Aqua.test_all(<PackageModule>)` to the test suite (inside the main `@testset` block) to prevent regressions.

Then run the full test suite and confirm it passes on both the lowest supported Julia version and the current release (see Step 2). Do not finish this step with a red suite on any supported version: if `Aqua.test_all` fails, return to Step 3.

## 5. Add Aqua badge to README

Add the following badge to the README (after any existing badges):

```
[![Aqua QA](https://juliatesting.github.io/Aqua.jl/dev/assets/badge.svg)](https://github.com/JuliaTesting/Aqua.jl)
```
