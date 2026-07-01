---
name: skill-creator
description: Author new BioRouter skills and improve existing ones — write the SKILL.md, get the description triggering reliably, structure bundled resources, and package for release. Use whenever the user wants to create a skill from scratch, edit or optimize a skill, fix a skill that won't trigger, or package a skill as a zip.
license: Apache-2.0
user-invocable: true
---

<!-- Adapted for BioRouter from anthropics/claude-plugins-official/plugins/skill-creator (Apache License 2.0). -->

# Skill Creator

The authoritative guide to authoring BioRouter skills. A skill is a folder with a `SKILL.md` plus optional bundled resources. Your job is to figure out where the user is — fresh idea, rough draft, or an existing skill that needs improving — and help them move forward.

High-level loop: decide what the skill should do → write a draft → test it by invoking it in BioRouter → refine based on what you observe → repeat → package. Stay flexible; if the user just wants to "vibe", skip the formal testing.

## Communicating with the user

Skill authors range from seasoned engineers to first-time terminal users. Read the context cues and match your phrasing. Briefly define jargon ("trigger", "frontmatter", "progressive disclosure") if you are unsure the user knows it. Don't lecture; explain just enough to keep them moving.

---

## The authoring spec

### Required frontmatter

Only two fields are parsed by BioRouter's skill loader: `name` and `description`. Other fields are ignored, but `user-invocable: true` is a useful convention for command-style skills — it surfaces as `/name` where supported and is harmless otherwise.

```
---
name: <kebab-case, must equal the folder name>
description: <one line — what it does AND when to use it>
user-invocable: true   # only for skills the user invokes directly
---
```

### The description is the primary trigger

The loader shows BioRouter every skill's name + description and lets the model decide whether to consult a skill. So the description *is* the triggering mechanism. It must state BOTH **what the skill does** AND **when to use it** — all "when to use" information lives here, not in the body.

Make it specific to fight under-triggering (the common failure: the skill exists but the model doesn't reach for it). Be a little pushy. List concrete trigger phrases and contexts.

- Weak: `"Build a dashboard for internal metrics."`
- Strong: `"Build a fast dashboard to display internal metrics. Use this whenever the user mentions dashboards, data visualization, internal metrics, or wants to display any kind of company data — even if they don't say 'dashboard'."`

### Progressive disclosure

Skills load in three levels. Put each piece of content at the cheapest level that works:

1. **Metadata** (name + description) — always in context. Keep it tight (~1-2 sentences).
2. **SKILL.md body** — loaded when the skill triggers. Aim for under ~500 lines. If you approach that, add a layer of hierarchy and point to bundled files.
3. **Bundled resources** — loaded on demand:
   - `references/` — docs the model reads only when relevant (for files over ~300 lines, add a table of contents at the top).
   - `scripts/` — executable helpers for deterministic or repeated work; can run without loading the file into context.
   - `assets/` — files used in the output (templates, icons, fonts).

When a skill spans multiple domains/frameworks, split by variant so only the relevant reference is read:

```
cloud-deploy/
├── SKILL.md          (workflow + which-variant selection)
└── references/
    ├── aws.md
    ├── gcp.md
    └── azure.md
```

### Writing style

- Use the **imperative voice** ("Run the tests", not "You should run the tests").
- Explain **why** an instruction matters instead of stacking heavy-handed `MUST`/`NEVER`. Modern models have good theory of mind; reasoning generalizes better than rigid rules. Repeated all-caps `ALWAYS`/`NEVER` is a yellow flag — reframe and explain.
- Keep it general, not overfit to one example. Draft, then reread with fresh eyes and cut what isn't pulling its weight.
- Skills must not contain malware, exploit code, or anything that would surprise the user given the skill's stated purpose.

### Define output formats with templates

When the skill produces structured output, give an exact template:

```markdown
## Report structure
Use this exact template:
# [Title]
## Executive summary
## Key findings
## Recommendations
```

### Include input/output examples

Examples anchor behavior. Show realistic input and the desired output:

```markdown
## Commit message format
Input:  Added user authentication with JWT tokens
Output: feat(auth): implement JWT-based authentication
```

### Bundle repeated helper logic as scripts

If, across uses, the model keeps writing the same helper (a `create_docx.py`, a chart builder, a data-cleaning step), write it once, drop it in `scripts/`, and tell the skill to call it. The agent can run shell commands and shipped helper scripts via BioRouter's Developer extension. If a skill needs actual tools or enforcement (not just instructions), it belongs in a `.brxt` extension — see the **develop-biorouter-extension** skill for that path.

---

## BioRouter specifics

### Discovery directories

BioRouter discovers skills in:
- `~/.config/biorouter/skills/`
- `./.biorouter/skills/` (project-local)
- `~/.claude/skills/`

Drop a skill folder into any of these and it's available.

### Packaging and release

Package a skill as a **zip whose root entry is the skill folder** — so the archive contains `myskill/SKILL.md`, not a bare `SKILL.md`. Name the asset `<name>.zip` and release it under the tag `skill-<name>`.

```bash
# from the directory that CONTAINS the skill folder
zip -r myskill.zip myskill/
# verify the root entry is the folder:
unzip -l myskill.zip   # first lines should show myskill/ and myskill/SKILL.md
```

If the skill ships tools or needs true enforcement, build the `.brxt` extension via the **develop-biorouter-extension** skill and reference it from the skill.

---

## Testing a skill in BioRouter

There is no `claude -p` eval harness here — test by actually using the skill.

1. Install the skill into a discovery dir (or point BioRouter at its folder).
2. Invoke it the way a real user would — type a request that *should* trigger it. If you have subagents available, spawn a BioRouter subagent with the request and observe what it does.
3. Check two things:
   - **Triggering** — did the skill fire on the intended request? Try 2-3 realistic phrasings, including casual ones and ones that don't name the skill explicitly.
   - **Output** — did it produce the target output/format?
4. Also test a couple of **near-miss** requests that should NOT trigger it (adjacent domains, shared keywords) to catch over-triggering.
5. **Iterate the description.** Under-triggering → make the description more specific and pushy, add the phrasing that failed. Over-triggering → narrow it, name what it is NOT for. The description is almost always the lever; change it and re-test.

Read the transcript, not just the final output. If the skill is making the model waste time on unproductive steps, cut the part of the skill causing it and re-test.

---

## Create checklist

- [ ] Capture intent: what should this enable, when should it trigger, what's the expected output. Mine the current conversation first if the user said "turn this into a skill".
- [ ] Choose the folder name (kebab-case) = the `name` field.
- [ ] Write the `description` with both what + specific when-to-use triggers; make it pushy.
- [ ] Add `user-invocable: true` if the user invokes it directly.
- [ ] Write the body in imperative voice, explaining the why; keep under ~500 lines.
- [ ] Define output templates and include input/output examples.
- [ ] Move long docs to `references/`, repeated logic to `scripts/`, output files to `assets/`.
- [ ] Test triggering (2-3 phrasings) and near-misses; test the output.
- [ ] Iterate the description until triggering is reliable.
- [ ] Package as `<name>.zip` (folder at root) and note the release tag `skill-<name>`.

## Improve checklist

- [ ] Reproduce the problem: is it under-triggering, over-triggering, or wrong output?
- [ ] If triggering: rework the description, not the body, first.
- [ ] Read recent transcripts; generalize from feedback rather than overfitting to one case.
- [ ] Cut instructions that aren't earning their place; reframe rigid `MUST`s into explained reasoning.
- [ ] Pull any repeated helper into `scripts/`.
- [ ] Preserve the skill's `name` and folder name when editing an installed skill (copy to a writeable location first if the install path is read-only).
- [ ] Re-test triggering + output; repackage and re-release under `skill-<name>`.
