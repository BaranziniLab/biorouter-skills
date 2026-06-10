# BioRouter Skills

A collection of **skills** for [BioRouter](https://github.com/BaranziniLab/BioRouter) — UCSF's local-first AI workspace for biomedical research.

Skills are reusable instruction bundles that BioRouter loads on demand to shape how the model writes code, drafts documents, reasons about a problem, and runs research. Some run automatically when relevant files are touched (style enforcement, language conventions, bioinformatics tasks). Others are *user-invocable* and respond to a slash command like `/ralph`, `/auto-research`, or `/anti-ai-writing` in the chat panel.

This repository hosts the skills curated by the [Baranzini Lab](https://baranzinilab.ucsf.edu/) at UCSF. Each top-level folder is a single skill; a few folders (`superpowers/`, `bio-skills/`) are bundled collections of many sub-skills.

---

## Installing a skill

1. Download the skill's `.zip` from the [Releases](https://github.com/BaranziniLab/biorouter-skills/releases) page.
2. Unzip it.
3. Move the resulting folder into `~/.config/biorouter/skills/`.
4. Open BioRouter. The skill appears under **Skills** automatically. User-invocable skills respond to `/skill-name`.

You can also drag a `.zip` (or a single `SKILL.md`) onto **Skills → Add Skill** inside BioRouter, or clone individual folders directly into `~/.config/biorouter/skills/` to track updates with `git`.

---

## Core skills

General-purpose skills — research, writing, planning, code style, and design.

| Skill | Trigger | What it does |
|---|---|---|
| [`scientific-research`](scientific-research) | `/scientific-research` | End-to-end research pipeline: scope → literature review → hypotheses → analysis plan → verification → cited write-up. Orchestrates `bio-skills` and the BioRouter extensions; never fabricates citations or results. |
| [`anti-ai-writing`](anti-ai-writing) | `/anti-ai-writing` | Pass/fail checklist that strips AI tells out of prose, articles, and essays. |
| [`taste-skill`](taste-skill) | Auto (frontend design) | Anti-slop frontend design — landing pages, portfolios, dashboards, and paper companion sites that don't look templated. |
| [`develop-biorouter-extension`](develop-biorouter-extension) | `/develop-biorouter-extension` | Step-by-step guide for building a `.brxt` extension — manifest, MCP server, bundled skills. |
| [`ralph`](ralph) | `/ralph` | End-to-end planning for the **Ralph** autonomous agent loop — generates a markdown PRD from a feature idea, then converts it to `prd.json` sized for one-story-per-iteration execution. |
| [`ucsf-hpc`](ucsf-hpc) | `/ucsf-hpc` | SSH setup, SLURM templates (CPU/GPU/H200), file transfer, and module management for the UCSF CHPC cluster. |
| [`python-scripting`](python-scripting) | Auto (Python) | Enforces Python naming, typing, error handling, and project-structure conventions. |
| [`r-scripting`](r-scripting) | Auto (R) | Tidyverse conventions and documentation standards for R. |
| [`ggplot-visualization`](ggplot-visualization) | Auto (R plotting) | Applies the lab's ggplot2 style whenever R plotting code is written. |
| [`superpowers`](superpowers) | Mixed | A bundled collection of 13 engineering-discipline skills (brainstorming, TDD, systematic debugging, parallel agents, plan writing, code review, git worktrees, more). |

---

## Developer & authoring skills

Engineering, review, and skill-authoring tools — adapted from [Anthropic's official Claude Code plugins](https://github.com/anthropics/claude-plugins-official) (Apache 2.0). Because BioRouter is a Goose fork with **no hook engine** and no `commands/`/`agents/` loaders, each upstream plugin's commands, subagents, and hooks have been folded into a single self-contained `SKILL.md` of agent instructions. Notably, `hookify` becomes a *self-enforced* guardrails skill rather than programmatic hooks.

| Skill | Trigger | What it does |
|---|---|---|
| [`code-review`](code-review) | `/code-review` | Multi-stage, confidence-scored review of a pull request (or local diff); drops low-confidence findings and posts a formatted PR comment via `gh`. |
| [`code-simplifier`](code-simplifier) | `/code-simplifier` | Simplifies recently-changed code for clarity while preserving exact behavior; defers language style to `python-scripting`/`r-scripting`. |
| [`commit-commands`](commit-commands) | `/commit-commands` | Three git workflows — clean single commit; commit + push + open PR; and clean up `[gone]` branches and their worktrees. |
| [`claude-md-management`](claude-md-management) | `/claude-md-management` | Captures session learnings into `CLAUDE.md`, and audits/scores existing project-memory files against a quality rubric. |
| [`skill-creator`](skill-creator) | `/skill-creator` | The canonical guide to authoring BioRouter skills — frontmatter, progressive disclosure, packaging, and testing. |
| [`hookify`](hookify) | `/hookify` | Captures project guardrails (warn/block rules) into `.biorouter/guardrails.md` that the agent self-enforces each turn (BioRouter has no hook engine). |
| [`code-modernization`](code-modernization) | `/code-modernization` | Phased legacy-modernization workflow: preflight → assess → map → extract rules → brief → transform → harden → status. |
| [`playground`](playground) | `/playground` | Generates self-contained single-file interactive HTML playgrounds for configuring something visually and copying out a prompt. |
| [`frontend-design`](frontend-design) | Auto (frontend work) | Anthropic's anti-slop frontend guidance; complements the `taste-skill`. |

---

## BioSkills — bioinformatics bundle

[`bio-skills/`](bio-skills) is a large, context-triggered bundle covering the working biologist's toolkit: sequence I/O, alignment, variant calling, single-cell, ATAC/ChIP-seq, proteomics, metabolomics, pathway analysis, machine learning, workflow management, and 60+ more categories (450+ individual skills). These load automatically when BioRouter sees a relevant file or task (a `.vcf`, a `scanpy` import, a `Seurat` object). See [`bio-skills/INDEX.md`](bio-skills/INDEX.md) for the full catalog.

Integrated from [GPTomics/bioSkills](https://github.com/GPTomics/bioSkills) (MIT). BioRouter's house style prefers [`uv`](https://github.com/astral-sh/uv) over `pip`; skills with `pip install` lines carry a one-line uv tip banner while leaving the original commands intact for reproducibility.

`scientific-research` is designed to delegate to this bundle — and to the SPOKE, CDW, OMOP, and MedCP extensions — for any biomedical data access, so the orchestrator never has to recall facts from memory.

---

## Repository layout

```
biorouter-skills/
├── LICENSE                        ← MIT
├── auto-research/SKILL.md
├── anti-ai-writing/SKILL.md
├── taste-skill/SKILL.md
├── develop-biorouter-extension/SKILL.md
├── ggplot-visualization/SKILL.md
├── python-scripting/SKILL.md
├── r-scripting/SKILL.md
├── ucsf-hpc/SKILL.md
├── ralph/
│   ├── SKILL.md                   ← the skill itself
│   ├── agent-instructions.md      ← prompt for the autonomous loop
│   └── prd.json.example
├── superpowers/                   ← 13 sub-skill collection
│   ├── brainstorming/
│   ├── test-driven-development/
│   └── …
└── bio-skills/                    ← bioinformatics bundle (60+ categories)
    ├── INDEX.md
    ├── single-cell/
    ├── variant-calling/
    └── …
```

Every skill folder contains a `SKILL.md` with YAML frontmatter (`name`, `description`, optional `user-invocable`). Anything else in the folder is supporting material the skill can reference.

---

## Contributing a new skill

1. Fork this repo.
2. Add a new top-level folder named after your skill (kebab-case).
3. Drop a `SKILL.md` into it with frontmatter:

   ```markdown
   ---
   name: my-skill
   description: One sentence — what it does and when to use it. This is the line the model reads to decide whether to load the skill.
   user-invocable: true   # optional
   ---

   # My Skill

   The skill body. Be concrete, give examples, and keep it focused on one job.
   ```

4. Open a pull request. A maintainer will review and cut a release with a matching `.zip` so BAAM picks it up automatically.

A good `description:` is the single most important line — it is what the model sees when deciding whether to invoke the skill, so be specific about *when* to use it, not just *what* it does.

---

## License & attribution

This repository is licensed under the [MIT License](LICENSE). Some skills are adapted from upstream open-source libraries and retain their original terms:

- **`bio-skills/`** — from [GPTomics/bioSkills](https://github.com/GPTomics/bioSkills) (MIT).
- **`taste-skill/`** — from [Leonxlnx/taste-skill](https://github.com/Leonxlnx/taste-skill) (MIT).
- **`superpowers/`** — adapted from the open-source "superpowers" Claude Code skill library.
- **Developer & authoring skills** (`code-review`, `code-simplifier`, `commit-commands`, `claude-md-management`, `skill-creator`, `hookify`, `code-modernization`, `playground`, `frontend-design`) — adapted from [anthropics/claude-plugins-official](https://github.com/anthropics/claude-plugins-official) (Apache 2.0). Each `SKILL.md` notes its source in a header comment.

Maintained by the [Baranzini Lab](https://baranzinilab.ucsf.edu/) at UCSF.
