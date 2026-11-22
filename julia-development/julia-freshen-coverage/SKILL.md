---
name: julia-freshen-coverage
description: "Measure and raise a Julia package's test coverage, writing tests for the important untested paths. Use when freshening a package or when the user asks about coverage."
license: Apache-2.0 AND MIT
user-invocable: true
metadata:
  version: "1.0.0"
  origin: "adapted"
  upstream: "timholy/claude_config/skills/freshen-coverage@225ce60094c1ecb823b3cb7abf2fd390185643ef"
  upstream_licence: "MIT"
---

<!-- Adapted for Biorouter from timholy/claude_config (skills/freshen-coverage, commit 225ce60094c1), MIT. Changes: renamed with a julia- prefix; Claude Code paths, slash commands and subagent names replaced with Biorouter equivalents. See LICENSE-UPSTREAM. -->

## 1. Run tests with coverage

Run the test suite with coverage enabled, typically by

```
julia --project -e 'using Pkg; Pkg.test(; coverage=true)'
```

There may be some exceptions, e.g., GUI packages that might require `xvfb-run`.

## 2. Analyze coverage

Analyze the results using CoverageTools.jl:

```julia
import Pkg; Pkg.activate(; temp=true); Pkg.add("CoverageTools")
using CoverageTools
coverage = process_folder("src")
covered, total = get_summary(coverage)
println("Coverage: $(round(100*covered/total, digits=1))%")
for fc in coverage
    for (line, hits) in enumerate(fc.coverage)
        if hits === 0
            println("$(fc.filename):$line")
        end
    end
end
```

## 3. Report findings

Summarize for the user:
- Overall coverage percentage
- Files/functions with meaningful gaps (ignore genuinely untestable code such as unreachable error paths)

## 4. Propose tests

Design tests to cover the gaps. Keep in mind:
- `@test_throws` should test the user-visible error message, not just the error type
- Printing tests should not be sensitive to whitespace changes
- Add `@inferred` for results used in performance-critical settings
- The purpose of tests is to make development more robust. Avoid tests that would make future development more brittle.

**Wait for user approval before writing any tests.**

## 5. Implement approved tests

Delete all `.cov` files generated in step 1:
```
find . -name "*.jl.cov" -o -name "*.jl.*.cov" | xargs rm -f
```

Then add the approved tests to the test suite and verify they pass.

## 6. Re-check coverage

Re-run tests with coverage (step 1) and re-run the analysis (step 2) to verify the expected improvements. Clean up `.cov` files again before proceeding:
```
find . -name "*.jl.cov" -o -name "*.jl.*.cov" | xargs rm -f
```
