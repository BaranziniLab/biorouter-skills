# BioSkills — Bioinformatics Skill Bundle

A comprehensive collection of bioinformatics skills for BioRouter, integrated from [GPTomics/bioSkills](https://github.com/GPTomics/bioSkills) (MIT-origin upstream) and distributed in this repository under Apache-2.0 with provenance preserved. Covers sequence I/O, alignment, variant calling, single-cell, ATAC/ChIP-seq, proteomics, metabolomics, machine learning, workflow management, and 50+ more categories.

## Install

```bash
# Clone the biorouter-skills repo
git clone https://github.com/BaranziniLab/biorouter-skills ~/.config/biorouter/skills-src

# Symlink the bio-skills bundle into your BioRouter skills directory
ln -s ~/.config/biorouter/skills-src/bio-skills ~/.config/biorouter/skills/bio-skills
```

Skills load automatically when BioRouter sees a relevant file or task (e.g., a `.vcf`, a `Seurat` import, a `pip install scanpy` request). The `user-invocable: false` frontmatter marks them as context-triggered, not slash commands.

## Prefer `uv` over `pip`

Many bioSkills examples install packages with `pip install ...`. BioRouter's house style prefers [`uv`](https://github.com/astral-sh/uv) — it's roughly 10-100× faster and produces reproducible installs.

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
license: Apache-2.0
tool_type: <python | r | cli | mixed>
primary_tool: <main package or CLI tool>
user-invocable: false
---
```

## Attribution & License

Upstream content authored by the GPTomics community originated under MIT. The BioRouter-distributed bundle is licensed under Apache-2.0 and keeps upstream provenance in the top-level attribution table. See [GPTomics/bioSkills](https://github.com/GPTomics/bioSkills) for contributing guidelines and full upstream attribution.

The BioRouter integration changes are:
1. Stripped the `bio-` prefix from the `name:` field so directory name matches skill name (matches the `superpowers/` bundle convention).
2. Added `user-invocable: false` and the uv tip banner described above.
3. Added `license: Apache-2.0` frontmatter for registry and installer visibility.

All skill content, examples, and command sequences are preserved as authored.
