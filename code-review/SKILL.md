---
name: code-review
description: "Review a pull request or a local diff for high-signal problems: bugs, logic errors, project-instruction violations, security vulnerabilities and silently swallowed errors, with optional test-coverage and critical-review passes. Every candidate issue is validated before it is reported. Prints the findings in the chat by default; posts inline pull request comments only when asked (--comment). Use when asked to review a PR, a branch, or the working-tree diff."
license: Apache-2.0 AND MIT
user-invocable: true
metadata:
  version: "1.1.0"
  origin: adapted
  upstream: "anthropics/claude-plugins-official/plugins/code-review@73c8cf3ea7e296057b467990f2f5d61b4c922260 (v1.0.1, c905cd8 command); plugins/pr-review-toolkit and plugins/security-guidance at the same commit; posit-dev/skills/posit-dev/critical-code-reviewer and review-testing@951959403f4ecc9d0274adf35538fc67153b6f31"
---

<!-- Adapted for Biorouter from anthropics/claude-plugins-official plugins/code-review (the c905cd8 command, v1.0.1), with passes from its pr-review-toolkit and security-guidance plugins (all Apache-2.0) and from posit-dev/skills critical-code-reviewer and review-testing (MIT). Licences in LICENSE-UPSTREAM. -->

# Code review

Review a pull request, a branch or a local diff, and report only issues you are confident are real. Run shell commands through the Developer extension; the pull request flow needs the `gh` CLI, authenticated. Make a todo list first, then work through the steps in order.

**Output goes to the chat unless the person asks to post.** Treat "post it", "comment on the PR" or a `--comment` argument as the request to post. Without it, never write to GitHub.

**No pull request?** For a branch or the working tree, gather the diff with `git diff <base>...HEAD` or `git diff HEAD`, skip steps 1 and 7, and run the rest.

## 1. Eligibility (pull requests)

Run `gh pr view <PR> --json state,isDraft,author,title,body,comments,reviews`. Stop and say why if:

- the pull request is closed or merged, or a draft;
- it needs no review (an automated dependency bump, or a trivial change that is obviously correct);
- you have already left a review on it.

Still review pull requests that an AI wrote.

## 2. Project instructions

List the paths (not contents) of the instruction files that apply: `AGENTS.md`, `CLAUDE.md` and `.biorouterhints` at the repository root and in every directory the change touches. A rule applies to a file only when the instruction file sits in that file's directory or a parent.

## 3. Summarise the change

Read `gh pr diff <PR>` (or the local diff) and the title and description, and write a short summary of what the change does and why. Give every pass below the title, description and summary, so each knows the author's intent.

## 4. Independent passes

Run the passes in parallel with Biorouter's `subagent` tool when it is offered (one subagent per pass, each told the tools work and to make only the calls it needs); otherwise run them yourself, one at a time, without carrying conclusions from one to the next. Each pass returns candidate issues, each with a description, the file and lines, and why it was flagged.

1. **Instruction compliance (two passes).** Audit the change against the instruction files from step 2. Flag only a rule you can quote exactly.
2. **Bug scan, diff only.** Read only the diff. Flag significant bugs you can confirm without outside context.
3. **Introduced-code problems.** Look for incorrect logic and other problems inside the changed code.
4. **Security.** Check the changed code against `references/security-pass.md`: injection, path traversal, authorisation gaps, secrets in logs or URLs, unsafe deserialisation, disabled TLS, SSRF, XSS and the rest. Flag only what the change introduces, or newly routes data into.
5. **Silent failures.** For a change that adds or edits error handling, fallbacks or retries, follow `references/silent-failure-pass.md`: empty catches, errors logged and dropped, fallbacks that hide a failure, broad catches.

Optional passes, only when the person asks or the project's instructions require them:

6. **Test coverage.** `references/test-coverage-pass.md` and `references/review-testing.md`: behaviour the change adds without a test, tests that test nothing, missing edge and failure cases. Report these under "Test gaps", separate from defects.
7. **Critical review.** When the person asks for a harsh or very thorough review, add the pass in `references/critical-code-reviewer.md`.

**Only high-signal issues.** Flag code that will fail to compile or parse, code that gives wrong results whatever the input, a security hole with a concrete path for an attacker, or a clear instruction violation you can quote. Do not flag style, issues that depend on unlikely inputs, or suggestions. If you are not sure an issue is real, leave it out.

## 5. Validate every candidate

For each candidate from passes 2 to 7, check it again independently (a fresh subagent per issue when the subagent tool is offered): is the stated problem really there, in this code, with high confidence? For instruction issues, confirm the rule covers that file and is really broken. Drop anything not confirmed.

Always exclude:

- issues that existed before the change, or sit on lines the change did not touch;
- anything that looks wrong but is correct;
- nitpicks a senior engineer would not raise;
- anything a linter, type checker or compiler catches (do not run them to check);
- general quality concerns (test coverage, security in untouched code) unless the instructions require them or the person asked for that pass;
- issues the code explicitly silences (a lint-ignore comment).

## 6. Report in the chat

- Issues found: one line each, with the file and line, what is wrong, and why it matters. Group as Bugs, Security, Instruction violations, Silent failures, then Test gaps if that pass ran.
- None found: "No issues found. Checked for bugs, security and project-instruction compliance."

Stop here unless the person asked to post.

## 7. Post to the pull request (only when asked)

Re-run step 1 first: the pull request may have closed while you worked.

- No issues: write "## Code review", a blank line and "No issues found. Checked for bugs, security and project-instruction compliance." to `comment.md` in a temporary folder outside the repository, then `gh pr comment <PR> --body-file comment.md`.
- Issues: post one review with one inline comment per unique issue. Write the comments to `review.json` in a temporary folder outside the repository and send them with `gh api repos/<owner>/<repo>/pulls/<PR>/reviews --method POST --input review.json`, where the file holds `{"commit_id": "<full head sha>", "event": "COMMENT", "body": "Code review", "comments": [{"path": "<file>", "line": <n>, "side": "RIGHT", "body": "<comment>"}]}`.
- Each comment: a short description of the issue and the fix. Add a committable suggestion block only for a small, self-contained fix that resolves the issue completely; describe larger fixes in words.
- Cite each issue. Link code as `https://github.com/<owner>/<repo>/blob/<full sha>/<path>#L<start>-L<end>`, with the full 40-character sha and at least one line of context on each side, and link any instruction file you quote.

## Hard rules

- Do not build, type-check or run the project for the review; CI does that.
- Use `gh` for GitHub, not web fetches.
- Never post without the person's request, and never post the same issue twice.
- For language-specific judgement, `python-scripting` and `r-scripting` hold the house style.

## Related skills

- `superpowers` → `requesting-code-review` dispatches a reviewer during development and `receiving-code-review` handles the answers; when the review is of a pull request or a finished diff, they should run this skill.
- `code-simplifier` cleans up code after a review; `commit-commands` opens the pull request this skill reviews.
- `references/upstream-command.md` keeps the upstream command for comparison.
