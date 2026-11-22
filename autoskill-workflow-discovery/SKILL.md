---
name: autoskill-workflow-discovery
description: Detect repeated user workflows and draft native Biorouter skills, hooks, or checklist updates from observed work patterns. Use when users ask to turn repeated work, screen-history patterns, project routines, or recurring guardrails into reusable Biorouter skills.
user-invocable: true
license: Apache-2.0
metadata:
  version: "1.1.0"
  origin: native
  upstream: "none (native rewrite, no upstream text copied)"
---

# Autoskill Workflow Discovery

Source adaptation: Biorouter-original synthesis inspired by the K-Dense Scientific Agent Skills autoskill idea, rewritten under Apache-2.0; no upstream text is copied.

## When to Use

Use this skill when the user wants to convert repeated work into a reusable Biorouter skill, project hook, checklist, or template. This is for pattern mining and skill drafting, not for silently installing automation.

## Intake

Collect:

- The repeated workflow or recent examples to inspect.
- Trigger conditions: files, phrases, repo paths, apps, data types, or task stages.
- Desired output: new skill, update to an existing skill, hook proposal, checklist, template, or registry plan.
- Safety boundaries: what must never be automated, what requires confirmation, and what can be auto-applied.
- Ownership and destination repo.

## Discovery Pass

1. Identify repeated decision points, not just repeated commands.
2. Separate stable domain knowledge from project-specific preference.
3. Record the inputs the model needs before acting.
4. Record the output shape the user repeatedly wants.
5. Identify checks that can be enforced as Biorouter hooks and checks that should remain advisory.
6. Keep external credentials, private datasets, and PHI out of the skill body.

## Hand-off to drafting

This skill finds and justifies the pattern; it does not own the skill format. Once a pattern passes the review gates below, load the built-in `develop-biorouter-skill` and let it write the skill: frontmatter, a description that triggers, progressive disclosure into supporting files, trigger and execution tests, and packaging. Hand it the evidence from the discovery pass, the intake answers and the boundaries, so the draft starts from observed work rather than from a blank template.

## Biorouter Output Choices

- Use a top-level `SKILL.md`, drafted with `develop-biorouter-skill`, when the pattern is reusable across projects.
- Use a project hook in `.biorouter/hooks.yaml` when a guardrail should warn or block.
- Use the built-in `develop-biorouter-extension` when repeated work needs tools, APIs, credentials, or local compute.
- Use `scientific-research`, `replication-package-audit`, or a domain Biomedical bundle as the parent route when the workflow is scientific.

## Skill Draft Checklist

`develop-biorouter-skill` has the full format checklist. Every proposed skill must also include:

- `name`, `description`, a `license` line that matches any adapted material, and appropriate `user-invocable`.
- A precise "When to Use" section.
- Intake questions.
- Routing rules to existing Biorouter skills/extensions.
- Verification gates.
- A response shape.
- Provenance and license notes.

## Review Gates

Before recommending installation:

1. Show exactly what pattern was observed and what evidence supports it.
2. Explain why an existing Biorouter skill is not enough.
3. Mark private/project-specific details for removal.
4. Prefer a small first version that can be tested on one real task.
5. Ask before creating hooks that warn/block user actions.
