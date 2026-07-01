---
name: code-modernization
description: Phased legacy-modernization workflow for COBOL, legacy Java/C++, and monoliths — assess, map, extract business rules, plan, transform module-by-module, and harden. Use when the user wants to understand, document, or modernize a legacy system.
license: Apache-2.0
user-invocable: true
---

<!-- Adapted for BioRouter from anthropics/claude-plugins-official/plugins/code-modernization (Apache License 2.0). -->

# Code Modernization

A disciplined, phased workflow for modernizing legacy systems (COBOL, JCL, RPG, legacy Java/EJB/Struts, classic C/C++, .NET, monoliths). The legacy system is the *specification source*, not the structural template. Each phase writes artifacts under `analysis/<system>/` so the work is resumable, auditable, and approvable.

Throughout, **write and run your own one-off analysis scripts** (Python or shell) at runtime rather than relying on shipped assets. Save each script alongside its output so it can be re-run and reviewed. You can run shell commands and helper scripts via BioRouter's Developer extension, and open generated HTML with `open`.

For any phase that benefits from a focused, independent pass, spawn a BioRouter subagent in natural language (e.g. "use a subagent acting as a security auditor to adversarially review this module"). Useful subagent roles, folded in below where they apply:

- **legacy-analyst** — deep-reads legacy code; reads entry points before grepping, cites every claim as `file:line`. Understanding, not judgment.
- **business-rules-extractor** — mines calculations, validations, eligibility, state transitions, and policies into Given/When/Then form; separates what the business requires from how the old code happened to implement it.
- **architecture-critic** — adversarial reviewer of target designs and transformed code; hunts over-engineering, missed requirements, and simpler alternatives.
- **security-auditor** — adversarial OWASP/CWE/CVE reviewer; traces user input to every sink.
- **test-engineer** — writes characterization tests where the legacy code is the oracle; concrete input → expected output, covering the edges the legacy covers.

Convention below: `<system>` is the system directory name; legacy source lives under `legacy/<system>/`, artifacts under `analysis/<system>/`, transformed output under `modernized/<system>/`.

---

## Phase 1 — Preflight

Goal: confirm the environment can analyze and eventually transform the system, and tell the user exactly what to fix first. Modernization sessions fail late and confusingly when this is skipped — metrics silently degrade, characterization tests can't run, dependency maps come out wrong. Run every check even when an early one fails; produce one complete readiness report.

1. **Detect the stack.** Fingerprint `legacy/<system>/` from file extensions and manifests: languages, build system, deployment/config descriptors. Report what was detected and the rough file split.
2. **Analysis tooling — degrade gracefully.** For each optional tool, check availability with `command -v` and report version + what degrades without it. None are required:
   - `scc` (or `cloc`) — LOC/complexity for assess; without it fall back to `find` + `wc -l` grouped by extension, and a coarser COCOMO estimate.
   - `lizard` — cyclomatic complexity; without it estimate from decision-keyword counts.
   - `delta` — side-by-side diffs in transform; without it fall back to `diff -y`.
   - `glow` — pretty markdown rendering; without it artifacts read as plain text (fine).
   Include the platform install one-liner for anything missing (`brew install scc`, `apt install cloc`, `pip install lizard`, …).
3. **Build toolchain — smoke test, not just presence.** Identify the legacy compiler/interpreter (GnuCOBOL `cobc`, JDK + Maven/Gradle, `cc`/`make`, `dotnet`) and prove it works on this code: pick one representative file and run a syntax-only compile (`cobc -fsyntax-only`, `javac`, `gcc -fsyntax-only`). A failed smoke test is the most valuable output — report the actual error and diagnose it (missing copybook/include path, missing dialect flag like `-std=ibm`, fixed vs free format, missing dependency jar). If a target stack was named, smoke-test its runtime, package manager, and test framework too.
4. **Source completeness.** Check for referenced-but-missing includes (copybooks `COPY X` with no file, missing headers/imports), and missing deployment/config descriptors. The dependency map is only as good as what's in the tree.

Write `analysis/<system>/PREFLIGHT.md`. Tell the user what to fix before continuing.

---

## Phase 2 — Assess

Goal: full discovery — inventory, complexity, tech debt, effort estimate.

- **Inventory & complexity.** Run `scc`/`cloc` for LOC by language; `lizard` for mean and max cyclomatic complexity (CCN). Fall back as described in preflight and note which tool you used. Capture total SLOC, dominant language, file count, mean/max CCN.
- **Tech debt & dependency freshness.** Locate the manifest (`pom.xml`, `*.csproj`, `requirements*.txt`, copybook dir) and note its age and pinned-version count. Count source files with vs without a header comment block for documentation coverage; list the top undocumented subsystems.
- **Effort estimate.** Compute person-months with COCOMO-II basic: `PM = 2.94 × (KSLOC)^1.10`. Show the formula and inputs so the figure is defensible.
- **Domains.** Group modules into business domains — these feed the topology map.

Write `analysis/<system>/ASSESSMENT.md` and a Mermaid `ARCHITECTURE.mmd`. For a portfolio of systems, sweep each immediate subdirectory and emit a color-graded heat-map HTML (one row per system: Lang, KSLOC, Files, Mean/Max CCN, Dep Freshness, Doc Coverage, COCOMO PM, Risk) plus a sequencing recommendation.

---

## Phase 3 — Map

Goal: dependency and topology map of how the pieces connect — the map an engineer needs before touching anything. Render it as a self-contained interactive HTML viewer.

**Write your own one-off analysis script** (`analysis/<system>/extract_topology.py` or `.sh`) that parses `legacy/<system>/` and extracts four datasets. Three principles, or the map misleads:

1. **Edges live in two places** — direct calls in source *and* dispatcher/router calls whose targets are variables (config tables, route maps, DI, dynamic dispatch). Resolve variables against config before declaring an edge unresolvable.
2. **The code↔storage join is usually external config**, not source — job/deployment descriptors map logical names to physical stores.
3. **Entry points usually live in deployment config**, not source — without parsing it, every top-level module looks unreachable.

Extract: **call graph** (direct `CALL`/method/`import` *and* dispatch `EXEC CICS LINK/XCTL`, DI wiring, routing, reflection — resolve variable targets against route tables/copybooks/config); **data dependency graph** (module ↔ data store, joined through config: `SELECT…ASSIGN TO` ↔ JCL `DD`, `EXEC CICS READ/WRITE…FILE()` ↔ CSD, `EXEC SQL` table refs, ORM mappings, model files; include UI/screen bindings); **entry points** (JCL `EXEC PGM=`, CICS CSD, `web.xml`/route annotations, `main()`, queue/scheduler subscriptions); **dead-end candidates** (no inbound edges — only meaningful once all entry-point and edge types are in the graph; suppress the dead claim for anything that could be the target of an unresolved dynamic call). For fixed-column source (COBOL columns 8–72, RPG), slice the code area and strip comment lines before regex matching, or you'll match sequence numbers and commented-out code.

Have the script write `analysis/<system>/topology.json` and print a human summary (cap ~200 lines). Schema:

```json
{
  "system": "<display name>",
  "root": { "id": "sys", "name": "<system>", "kind": "system", "children": [
    { "id": "dom:<domain>", "name": "<Domain>", "kind": "domain", "children": [
      { "id": "<MODULE>", "name": "<MODULE>", "kind": "module",
        "language": "cobol", "loc": 1234, "file": "src/MODULE.cbl" } ] },
    { "id": "dom:data", "name": "Data stores", "kind": "domain", "children": [
      { "id": "ds:<NAME>", "name": "<NAME>", "kind": "datastore" } ] } ] },
  "edges": [ { "source": "<id>", "target": "<id>", "kind": "call" } ],
  "entryPoints": ["<id>"], "deadEnds": ["<id>"],
  "observations": ["<architect observation>"],
  "flows": [ { "name": "<business flow>", "persona": "<who>",
    "description": "<one sentence>",
    "steps": [ { "label": "<business-language step>", "nodes": ["<id>"] } ] } ]
}
```

Leaf kinds: `module`, `datastore`, `job`, `screen`; `loc` drives node size. Edge kinds: `call`, `dispatch`, `read`, `write` — every endpoint must be an existing leaf id. **Datastore ids/names must be logical identifiers** (DD name, dataset, table/schema, at most host:port) — strip userinfo and credential query params from any resolved DSN/URL; the file gets committed. Add 3–7 architect `observations` (coupling clusters, single points of failure, extraction candidates, over-written stores, unresolved dispatch). Trace 2–4 end-to-end persona `flows` anchored to the people who *experience* the system (claimant, caseworker, auditor — not maintainers).

**Generate the interactive HTML viewer by writing it inline at runtime** — do not reference any shipped asset. After the script produces `topology.json`, write `analysis/<system>/TOPOLOGY.html` yourself: a single self-contained dark-theme file (all CSS/JS inline, no CDNs) that reads the topology data injected directly into the file, renders the tree/graph with sized nodes, colors edges by kind, dashes dead-ends, and shows observations and persona flows. Inject `topology.json` into the HTML (e.g. as an inline `<script>const DATA = {…}</script>`) rather than fetching it. Then `open analysis/<system>/TOPOLOGY.html`.

A subagent acting as a legacy-analyst can produce the call-flow tracing; one acting as an architecture-critic can sanity-check the observations.

---

## Phase 4 — Extract rules

Goal: mine business logic into testable, human-readable specifications — the institutional knowledge locked in code and in the heads of engineers about to retire. Prioritize calculation, validation, eligibility, and state-transition logic over plumbing.

Spawn **three subagents in parallel, each acting as a business-rules-extractor** with a different lens:

1. **Calculations** — every formula, rate, threshold, computed value: what it computes, inputs, exact formula, `file:line`, edge cases handled.
2. **Validations & eligibility** — every business validation, eligibility check, guard: what's checked, pass/fail behavior, `file:line`.
3. **State & lifecycle** — every status field, state machine, transition: states, triggers, side-effects.

Merge, deduplicate, and write each distinct rule as a Rule Card in `analysis/<system>/BUSINESS_RULES.md`:

```
### RULE-NNN: <plain-English name>
**Category:** Calculation | Validation | Lifecycle | Policy
**Priority:** P0 | P1 | P2
**Source:** `path/to/file.ext:line-line`
**Plain English:** One sentence a business analyst would recognize.
**Specification:**
  Given <precondition>
  When  <trigger>
  Then  <outcome>
**Parameters:** <constants/rates/thresholds with current values — credentials masked: `<credential — masked, see file:line>`>
**Edge cases handled:** <list>
**Suspected defect:** <optional — looks wrong; decide preserve-vs-fix during transform>
**Confidence:** High | Medium | Low — <why; if < High, the exact SME question>
```

Default Priority **P1**. Assign **P0** if the rule moves money, enforces a regulatory/compliance requirement, or guards data integrity (flag P0 rules under High confidence as SME-required). **P2** for display/formatting/convenience. The brief's behavior contract is built from the P0 rules.

---

## Phase 5 — Brief

Goal: the approved, phased modernization plan that transformation works against. Read `ASSESSMENT.md`, `topology.json`, and `BUSINESS_RULES.md` first; if any are missing, say so and stop (run the earlier phases). Note input timestamps in the header so reviewers see what it was built from.

Write `analysis/<system>/MODERNIZATION_BRIEF.md`:

1. **Objective** — from what, to what, why now.
2. **Target architecture** — Mermaid C4 Container diagram of the end state; a table mapping legacy component → target component(s). If no target stack was given, recommend one from the assessment.
3. **Phased sequence** — 3–6 phases in **strangler-fig order** (lowest-risk, fewest-dependencies first). Per phase: scope, entry/exit criteria, estimated effort (person-months, same unit as the COCOMO figure), risk level + top 2 risks + mitigation. Render as a Mermaid `gantt`.
4. **Business walkthroughs** — for each persona flow in `topology.json`, a narrative table: persona, what happens in business language, which legacy modules implement it today, which phase replaces each.
5. **Behavior contract** — the P0 rules from `BUSINESS_RULES.md` that MUST be proven equivalent before any module is considered done.

A subagent acting as an architecture-critic should review the target architecture for over-engineering and missed requirements before you finalize.

---

## Phase 6 — Transform

Goal: transform **one module at a time** to the target stack — an idiomatic rewrite plus proof of behavioral equivalence. One vertical slice of the strangler fig. Output to `modernized/<system>/<module>/`.

1. **Toolchain check — fail fast on target, adapt on legacy.** Verify the target runtime, package manager, and test framework all respond; if any are missing, stop and report what to install (the new code and its tests can't run without them). Try a syntax-only compile of the legacy module — but this is advisory, never a blocker: CICS/IMS programs often have no local translator. If legacy can't run locally, **equivalence becomes trace-based** — characterization tests assert against recorded traces / golden-master fixtures (real production outputs, captured reports/screens, SME-confirmed examples) instead of live legacy runs. Say so explicitly in the plan and in `TRANSFORMATION_NOTES.md` so reviewers know the strength of the proof.
2. **Plan (human gate).** Read the source module and the business rules referencing it. Present the plan — source files in scope, target module structure, which rules it implements, the equivalence strategy, and anything ambiguous needing a human decision now — and **write no code until the user approves**.
3. **Characterization tests FIRST.** Before any target code, have a subagent acting as a test-engineer write characterization tests: read the source, identify every observable behavior, encode each as concrete input → expected output derived from the legacy logic (the legacy code is the oracle — if it computes 19.27, assert 19.27 and flag any spec discrepancy separately). Target the appropriate framework; write to `modernized/<system>/<module>/src/test/`. These tests define "done."
4. **Reimplement idiomatically** in the target stack — not a line-by-line port. Make the new code pass every characterization test. Use `delta` (or `diff -y`) to present meaningful before/after where helpful.
5. **Document.** Write `modernized/<system>/<module>/TRANSFORMATION_NOTES.md`: what changed, the equivalence strategy and its strength, preserved-vs-fixed decisions on any suspected defects.

A subagent acting as an architecture-critic can review the freshly transformed module against modern best practice.

---

## Phase 7 — Harden

Goal: a security scan with a reviewable remediation patch. This phase never edits `legacy/` — it writes findings and a proposed patch to `analysis/<system>/`; the user reviews and applies (or not).

**Secrets quarantine first.** Findings get shared and committed, so discovered credential values must never land in them. Ensure `analysis/.gitignore` exists and contains `SECRETS.local.md` and `*.local.patch`; in a git repo verify with `git check-ignore -q analysis/<system>/SECRETS.local.md` before writing any findings. If there is no git repo, refuse to reveal secrets and write any sensitive file to `~/.modernize/<system>/` instead. All secret values in shareable artifacts are **masked** (`AKIA****`, `password=****`) and cited by `file:line`.

**Scan.** Spawn a subagent acting as a security-auditor: adversarially audit `legacy/<system>/` for what's relevant to the stack — injection (SQL/NoSQL/OS command/template), broken auth and session handling, sensitive data exposure, access-control gaps, insecure deserialization, hardcoded secrets, vulnerable dependency versions, missing input validation, path traversal. For each finding: CWE ID, severity (Critical/High/Med/Low), `file:line`, one-sentence exploit scenario, recommended fix. Run any available SAST tooling (`npm audit`, `pip-audit`, OWASP dependency-check) and include raw output. Mask every discovered credential value.

**Triage & remediate.** Write `analysis/<system>/SECURITY_FINDINGS.md`: a summary scorecard (counts by severity, top CWE categories), a findings table sorted by severity, and a dependency CVE table (package, installed version, CVE, fixed version). Produce a reviewable `analysis/<system>/security_remediation.patch` for the critical findings (raw secret values may appear only in gitignored `*.local.patch` hunks). Tell the user to review before applying.

---

## Phase 8 — Status

Goal: report where the modernization stands, in one screen. Read-only — inspect, never modify.

1. **Artifact inventory.** Check `analysis/<system>/` and `modernized/<system>*/`; build a table, one row per stage, with each artifact's presence and modification time — preflight (`PREFLIGHT.md`), assess (`ASSESSMENT.md`, `ARCHITECTURE.mmd`), map (`topology.json`, `TOPOLOGY.html`, `*.mmd`, `extract_topology.*`), extract-rules (`BUSINESS_RULES.md`), brief (`MODERNIZATION_BRIEF.md` — note whether the approval block is signed), harden (`SECURITY_FINDINGS.md`, `security_remediation.patch`), transform (each `modernized/<system>*/<module>/` dir — note test presence and `TRANSFORMATION_NOTES.md`).
2. **Staleness.** Flag any artifact older than an upstream input it derives from (brief older than assessment/topology/rules; `TOPOLOGY.html` older than `topology.json`; transformation notes older than the rules) and recommend the re-run.
3. **Secrets hygiene.** Confirm `analysis/.gitignore` covers the secret files; if `SECRETS.local.md` exists, confirm it is untracked and never committed (`git ls-files --error-unmatch`, `git log --all`) — if either fails, say so prominently and recommend rotation plus history scrubbing.
4. **Verdict** — three lines: **where you are** (furthest completed stage, rough coverage), **what's stale** (or "nothing"), **next step** (the single most useful next phase, with a one-line reason).

---

Cross-references: for the analysis scripts you write, lean on the sibling `python-scripting` and `r-scripting` skills; for any charts in reports, `ggplot-visualization`; for SME-facing research framing, `scientific-research`.
