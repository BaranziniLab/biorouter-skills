---
name: claude-md-management
description: Capture session learnings into project-memory files, or audit and improve existing CLAUDE.md files against a quality rubric. Use when the user asks to update, revise, capture, audit, check, improve, or fix CLAUDE.md / project memory, or says something like "save what we learned" or "tidy up the project memory".
user-invocable: true
---

<!-- Adapted for BioRouter from anthropics/claude-plugins-official/plugins/claude-md-management (Apache License 2.0). -->

# CLAUDE.md Management

Keep project-memory files sharp so future sessions start with the right context. This skill has two modes. Pick one based on what the user asked for; if it is ambiguous, ask which they want.

- **Capture mode** (quick): reflect on what this session taught you, then draft concise additions to the project-memory files. Use when the user wants to "save", "capture", or "revise with what we learned".
- **Audit mode** (thorough): discover every CLAUDE.md, grade each against a quality rubric, print a report, then make targeted edits. Use when the user wants to "audit", "check", "improve", or "fix" the project memory.

In both modes: never edit a memory file without showing the proposed change first and getting explicit approval.

## BioRouter note

CLAUDE.md is the primary project-memory file BioRouter reads. BioRouter also reads files under `~/.claude/` (e.g. `~/.claude/CLAUDE.md` for user-wide defaults). If the project uses a separate BioRouter hints file, apply the same practices to it. Everything here is about writing memory that is concise, repo-specific, and actionable — memory is part of the prompt, so brevity is a feature, not a compromise.

---

## Capture mode

### Step 1: Reflect on the session

Ask yourself what context was missing that would have helped you work more effectively from the start. Look for:
- Shell commands that were discovered or that turned out to be the right ones (build, test, run, lint, deploy)
- Code-style patterns the user steered you toward
- Testing approaches that actually worked here
- Environment or configuration quirks
- Warnings and gotchas you hit (and the fix)

Skip anything obvious from the code, generic best practice, or one-off fixes unlikely to recur.

### Step 2: Find the memory files

```bash
find . -name CLAUDE.md -o -name .claude.local.md 2>/dev/null | head -20
```

Decide where each addition belongs:
- `CLAUDE.md` — team-shared, checked into git
- `.claude.local.md` — personal/local only, gitignored

If no memory file exists and you have a worthwhile learning, propose creating `./CLAUDE.md`.

### Step 3: Draft concise additions

One line per concept. Format: `` `<command or pattern>` — <brief description> ``. Group related lines under a short heading if needed (Commands, Gotchas, Testing). Resist verbosity — if a one-liner suffices, use it.

### Step 4: Show the diff, then apply on approval

For each addition, show exactly what you propose to add and why:

```
### Update: ./CLAUDE.md

**Why:** <one-line reason this helps future sessions>

```diff
+ `npm run dev` — start dev server on port 3000 (not `npm start`)
```
```

Apply only the changes the user approves. Preserve existing structure.

---

## Audit mode

### Phase 1: Discover every memory file

```bash
find . -name CLAUDE.md -o -name .claude.local.md 2>/dev/null | head -50
```

Also consider `~/.claude/CLAUDE.md` (user-wide defaults) and `./packages/*/CLAUDE.md` in monorepos. BioRouter auto-discovers CLAUDE.md in parent directories, so nested files compose.

### Phase 2: Grade each file against the rubric

Evaluate every file on these criteria. Each is scored out of its weight; sum to 0–100 and map to a letter grade.

| Criterion | Weight | What to check |
|-----------|--------|---------------|
| Commands/workflows documented | 20 | Are build/test/run/deploy commands present and copy-paste ready? |
| Architecture clarity | 20 | Can a fresh session understand the structure and entry points? |
| Concrete & non-redundant | 15 | Project-specific, not generic; nothing restating the obvious code |
| Conciseness | 15 | No verbose explanations; dense beats wordy |
| Current | 15 | Does it match the codebase today (no stale commands/paths)? |
| Actionable | 15 | Are instructions executable, not vague advice? |

Grades: **A** 90–100 (comprehensive, current, actionable) · **B** 70–89 (good, minor gaps) · **C** 50–69 (basic, missing key sections) · **D** 30–49 (sparse/outdated) · **F** 0–29 (missing or severely stale).

### Phase 3: Print the quality report — always before any edit

```
## CLAUDE.md Quality Report

### Summary
- Files found: X
- Average score: X/100
- Files needing update: X

### File-by-File Assessment

#### 1. ./CLAUDE.md (Project Root) — Score: XX/100 (Grade: X)

| Criterion | Score | Notes |
|-----------|-------|-------|
| Commands/workflows | X/20 | ... |
| Architecture clarity | X/20 | ... |
| Concrete & non-redundant | X/15 | ... |
| Conciseness | X/15 | ... |
| Current | X/15 | ... |
| Actionable | X/15 | ... |

**Issues:** <specific problems>
**Recommended additions:** <what to add>
```

### Phase 4: Targeted edits, on approval

Propose only genuinely useful changes — discovered commands, real gotchas, unclear package relationships, working test approaches, config quirks. Keep them minimal. Show each as a diff with a one-line "why" (same format as Capture mode Step 4). Apply only approved changes and preserve existing structure.

Common issues to flag: stale build commands, missing required tools, outdated file structure, missing env/config setup, broken test commands, undocumented gotchas.

---

## What makes a great CLAUDE.md

- Concise and human-readable — dense is better than verbose; it is part of the prompt.
- Actionable commands that are copy-paste ready.
- Project-specific patterns and gotchas, not generic advice.

Recommended sections (use only what is relevant): Commands · Architecture · Key Files · Code Style · Environment · Testing · Gotchas · Workflow. Put personal-only preferences in `.claude.local.md` (gitignored); put user-wide defaults in `~/.claude/CLAUDE.md`.
