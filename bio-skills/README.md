# BioSkills — Bioinformatics Skill Bundle

A comprehensive collection of bioinformatics skills for Biorouter, integrated from [GPTomics/bioSkills](https://github.com/GPTomics/bioSkills) (MIT upstream, archived) and maintained here, with provenance preserved. Covers sequence I/O, alignment, variant calling, single-cell, ATAC/ChIP-seq, proteomics, metabolomics, machine learning, workflow management, and 50+ more categories (570 components in 63 bundles).

## Install

```bash
# Clone the biorouter-skills repo
git clone https://github.com/BaranziniLab/biorouter-skills ~/.config/biorouter/skills-src

# Symlink the bio-skills bundle into your Biorouter skills directory
ln -s ~/.config/biorouter/skills-src/bio-skills ~/.config/biorouter/skills/bio-skills
```

Skills load automatically when Biorouter sees a relevant file or task (e.g., a `.vcf`, a `Seurat` import, a `pip install scanpy` request). The `user-invocable: false` frontmatter marks them as context-triggered, not slash commands.

## Prefer `uv` over `pip`

Many bioSkills examples install packages with `pip install ...`. Biorouter's house style prefers [`uv`](https://github.com/astral-sh/uv) — it's roughly 10-100× faster and produces reproducible installs.

| Original | Preferred |
|---|---|
| `python -m venv .venv` | `uv venv .venv` |
| `pip install scanpy` | `uv pip install scanpy` (in a venv) or `uv add scanpy` (in a uv project) |
| `pip install -r requirements.txt` | `uv pip install -r requirements.txt` |
| `pipx install <tool>` | `uv tool install <tool>` |

Skills that contain `pip install` lines have a one-line uv tip banner at the top. The underlying commands are left intact so the original skill content stays reproducible if `uv` is unavailable.

## Layout

```
bio-skills/
├── README.md                  ← this file
├── INDEX.md                   ← every category and skill, alphabetical
├── alignment/
│   ├── pairwise-alignment/SKILL.md
│   └── ...
├── single-cell/
│   ├── clustering/SKILL.md
│   ├── cell-annotation/SKILL.md
│   └── ...
└── ... (61 more categories)
```

Each `SKILL.md` carries YAML frontmatter:

```yaml
---
name: <kebab-case-name>
description: <one-line "Use when ..." trigger>
license: Apache-2.0 AND MIT
tool_type: <python | r | cli | mixed>
primary_tool: <main package or CLI tool>
user-invocable: false
metadata:
  version: "1.1.0"
  upstream: "GPTomics/bioSkills@d91ed3d"
---
```

## Attribution and license

The bundles are adapted from [GPTomics/bioSkills](https://github.com/GPTomics/bioSkills) (MIT, Copyright (c) 2026 GPTomics), which was archived on 2026-08-15. Version 1.1.0 is a single final resync to its last commit, `d91ed3d`; from here on the lab maintains the bundles itself and does not expect further upstream changes. Components taken from other permissive projects (K-Dense, jsperger, Posit, Aperivue, OpenAI, marimo) are recorded in the catalog row of the bundle that holds them.

Every bundle carries a `LICENSE-UPSTREAM` file with the licence text and copyright notice of each upstream it redistributes, and that file travels inside the zip. The bundle as a whole is shown as `Apache-2.0 AND MIT`, and every `SKILL.md` says the same in its `license` line.

The Biorouter changes to upstream text are:
1. Removed the `bio-` prefix from the `name:` field (names of components that existed in 1.0.0 are unchanged, even where upstream later renamed them).
2. Added `license`, `user-invocable: false` and a `metadata` map (`version`, `upstream`) to the frontmatter, and the uv tip banner described above.
3. Spelled the product name "Biorouter", and pointed cross-references at components that still exist.
4. Removed or merged components that duplicated another (recorded as `removed` or `superseded_by` in the catalog row), and added the Biorouter originals and third-party components listed in each bundle's README.

All other skill content, examples and command sequences are preserved as authored.
