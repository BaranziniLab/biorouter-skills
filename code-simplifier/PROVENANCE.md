# Provenance and credits: Code Simplifier

<!-- Generated from catalog.json by scripts/render-readme.mjs. Do not edit by hand. -->

Adapted from code-simplifier plugin by Anthropic (Apache-2.0).

Includes text or code from the sources below, changed for Biorouter. Their licences and copyright lines ship with it.

## Sources

| Source | Commit or version | Licence | Credit and people | Use and what | Files | Via |
|---|---|---|---|---|---|---|
| [code-simplifier plugin](https://github.com/anthropics/claude-plugins-official): `anthropics/claude-plugins-official`, `plugins/code-simplifier` | commit `de573bd84695`, taken 2026-06-09 | Apache-2.0; no copyright line: the licence file (plugins/code-simplifier/LICENSE, LICENSE) names no copyright holder; the source has no NOTICE file; people: Boris Cherny is the commit author of ceb9b72 (2026-01-08), the only commit on plugins/code-simplifier/agents/code-simplifier.md, which added it with its own front matter; Noah Zweben is the commit author of 4ca561f (2025-11-20), where its body first appears, as plugins/pr-review-toolkit/agents/code-simplifier.md (the two bodies are the same at de573bd) | Anthropic; people: Boris Cherny, Noah Zweben | text: plugins/code-simplifier at de573bd: agents/code-simplifier.md, closely paraphrased as this item's SKILL.md; that file's body is the text of plugins/pr-review-toolkit/agents/code-simplifier.md, which Noah Zweben's commit 4ca561f (2025-11-20) added | `SKILL.md` |  |

Changes for Biorouter: The plugin's subagent prompt (agents/code-simplifier.md) rewritten as a user-invoked SKILL.md in close paraphrase: its list of one project's coding standards replaced by the project's own instructions and the python-scripting, r-scripting and bio-skills skills, its instruction to act on its own after every edit dropped, and an output section with before and after examples added.

## Contributors

- Wanjun Gu, Baranzini Lab, UCSF: adapted it for Biorouter

## Licences

The archive's LICENSE file is the Apache License 2.0; it covers Biorouter's own text in this folder. Copyright 2026 Baranzini Lab, University of California, San Francisco.
The item as a whole is licensed under Apache-2.0.
The copyright lines and licence texts of its sources are in LICENSE-UPSTREAM.

Curated and organized by Wanjun Gu, Baranzini Lab, UCSF.
