---
name: autoskill-workflow-discovery
description: Detect repeated user workflows and draft native BioRouter skills, hooks, or checklist updates from observed work patterns. Use when users ask to turn repeated work, screen-history patterns, project routines, or recurring guardrails into reusable BioRouter skills.
user-invocable: true
license: Apache-2.0
---

# Autoskill Workflow Discovery

Source adaptation: BioRouter-original synthesis inspired by Scientific Agent Skills workflow-discovery patterns, rewritten under Apache-2.0. Do not copy upstream text; use this as a native BioRouter skill-design and governance workflow.

## When to Use

Use this skill when the user wants to convert repeated work into a reusable BioRouter skill, project hook, checklist, or template. This is for pattern mining and skill drafting, not for silently installing automation.

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
5. Identify checks that can be enforced as BioRouter hooks and checks that should remain advisory.
6. Keep external credentials, private datasets, and PHI out of the skill body.

## BioRouter Output Choices

- Use a top-level `SKILL.md` when the pattern is reusable across projects.
- Use a project hook in `.biorouter/hooks.yaml` when a guardrail should warn or block.
- Use `develop-biorouter-extension` when repeated work needs tools, APIs, credentials, or local compute.
- Use `scientific-research`, `replication-package-audit`, or a domain BioSkill as the parent route when the workflow is scientific.

## Skill Draft Checklist

Every proposed skill must include:

- `name`, `description`, `license: Apache-2.0`, and appropriate `user-invocable`.
- A precise "When to Use" section.
- Intake questions.
- Routing rules to existing BioRouter skills/extensions.
- Verification gates.
- A response shape.
- Provenance and license notes.

## Review Gates

Before recommending installation:

1. Show exactly what pattern was observed and what evidence supports it.
2. Explain why an existing BioRouter skill is not enough.
3. Mark private/project-specific details for removal.
4. Prefer a small first version that can be tested on one real task.
5. Ask before creating hooks that warn/block user actions.
