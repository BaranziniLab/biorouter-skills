---
name: hookify
description: Capture project guardrails — rules that warn or block unwanted behaviors (destructive shell commands, debug prints, editing sensitive files, finishing without tests) — and self-enforce them each turn. Use when the user wants to add a guardrail, prevent a behavior, "stop doing X", or set up checks the agent should honor before acting.
user-invocable: true
---

<!-- Adapted for BioRouter from anthropics/claude-plugins-official/plugins/hookify (Apache License 2.0). -->

# Hookify (self-enforced guardrails)

## Read this first — the limitation

BioRouter does **not** execute programmatic hooks. There is no hook engine: PreToolUse / PostToolUse / Stop / UserPromptSubmit do not run. So the guardrails this skill creates are **conventions the agent itself honors each turn — not enforced gates.** A determined or forgetful agent can bypass them; they are a discipline, not a wall.

If you need *true* enforcement that cannot be skipped, it must live in a `.brxt` extension or a workflow validation step — see the **develop-biorouter-extension** skill. Use this skill when honor-system guardrails are good enough (the common case for "please stop doing X").

Be upfront with the user about this distinction when you set up rules, especially for `block` rules — a `block` here means "the agent refuses and explains", not "the system prevents it".

---

## Workflow: capturing rules

### 1. Gather candidate rules

Two sources:

- **Explicit instruction** — the user says "warn me when I use `rm -rf`" or "don't leave `console.log` in TypeScript". Turn that directly into a rule.
- **Conversation scan** — if the user just runs the skill with no specifics, scan the recent conversation for frustration or correction signals: places they said "no, don't do that", "you keep…", "I told you already", or had to undo your work. Each recurring correction is a candidate rule.

### 2. Confirm with the user

Present the candidate rules as a short list. For each, confirm:
- whether to add it,
- whether it's `warn` (surface a message, then proceed) or `block` (refuse and explain).

Don't write anything until the user signs off. Default to `warn` unless the behavior is genuinely destructive.

### 3. Write them to the project guardrails file

Append each confirmed rule to `./.biorouter/guardrails.md` (create the directory and file if missing). One rule per entry, in the format below.

---

## Rule file format

`./.biorouter/guardrails.md` holds simple markdown, one rule per entry. Each rule has:

- **name** — short identifier.
- **scope** — when it applies: `before-bash`, `before-edit`, `before-finish`, or `always`.
- **match** — the condition described plainly (a pattern, or a situation). Plain language is fine — you are the one checking it, not a regex engine.
- **action** — `warn` or `block`.
- **message** — what to surface when it matches.

Entry template:

```markdown
## <name>
- scope: <before-bash | before-edit | before-finish | always>
- match: <pattern or condition in plain language>
- action: <warn | block>
- message: <what to tell the user when this rule fires>
```

---

## Enforcement instruction

This is the part that makes the skill work, since nothing runs automatically:

**At the start of each turn, and again BEFORE any risky action** — running a shell command, editing a file, or declaring the task complete — read `./.biorouter/guardrails.md` (if it exists) and check the rules whose `scope` matches what you are about to do:

- `before-bash` rules: check before running any shell command.
- `before-edit` rules: check before editing or writing a file.
- `before-finish` rules: check before telling the user the task is done.
- `always` rules: check on every turn.

For each matching rule:
- **warn** → surface the rule's message to the user, then continue.
- **block** → do **not** take the action. Tell the user the rule blocked it, show the message, and explain the situation. Proceed only if the user explicitly overrides.

If `./.biorouter/guardrails.md` doesn't exist, there are no guardrails — carry on normally.

---

## Examples

### Block destructive shell commands

```markdown
## block-destructive-shell
- scope: before-bash
- match: command contains `rm -rf`, `dd if=`, `mkfs`, or `chmod 777`
- action: block
- message: Destructive command detected. This can cause data loss — verify the exact path and use a safer approach before proceeding.
```

### Warn on leftover debug code

```markdown
## warn-debug-code
- scope: before-edit
- match: new content adds `console.log(`, `debugger;`, or a stray `print(`
- action: warn
- message: Debug statement added — remember to remove it before committing.
```

### Warn before editing sensitive files

```markdown
## warn-sensitive-files
- scope: before-edit
- match: file path matches `.env`, `credentials`, or `secrets`
- action: warn
- message: Editing a sensitive file. Make sure no credentials are hardcoded and the file is gitignored.
```

### Require tests before finishing

```markdown
## require-tests-before-finish
- scope: before-finish
- match: no test command (e.g. `npm test`, `pytest`, `cargo test`) was run this session
- action: block
- message: Tests haven't been run this session. Run the test suite to verify the changes before declaring the task complete.
```

---

## Managing rules

- **List** rules: read `./.biorouter/guardrails.md` and summarize the entries.
- **Disable** a rule: with the user's OK, delete its entry (or comment it out) from the file.
- **Edit** a rule: change its `match`, `action`, or `message` in place.

Keep the file short and the rules specific — a long list of vague guardrails is easy to lose track of, and since enforcement is voluntary, focus on the few that matter most.
