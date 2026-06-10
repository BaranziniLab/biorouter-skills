---
name: commit-commands
description: Git commit workflows — create one focused commit; commit, push and open a PR; or clean up local branches whose remote is gone. Use when asked to commit, push and PR, or prune stale branches.
user-invocable: true
---

<!-- Adapted for BioRouter from anthropics/claude-plugins-official/plugins/commit-commands (Apache License 2.0). -->

# Commit commands

Three git workflows. Run all shell commands through the Developer extension. Requires
`git` (and `gh` for the PR flow). Pick the workflow that matches the request.

Keep commit messages clean and conventional (e.g. `fix: ...`, `feat: ...`). The lab may
optionally add a `Co-Authored-By:` trailer — if your environment expects one, append it;
otherwise keep the message tidy and don't invent one.

## Workflow 1 — Commit

First gather context (this replaces the original's automatic context injection):

```bash
git status
git diff HEAD
git branch --show-current
git log --oneline -10
```

Then create exactly ONE focused commit:
- Stage the relevant changes with `git add`.
- Write a single clear message summarizing the change.
- Do NOT add unrelated files. If the working tree mixes concerns, stage only the files
  that belong to this commit.
- Commit with `git commit`.

Do the staging and commit, then stop. Don't do anything beyond this.

## Workflow 2 — Commit, push & PR

Gather context:

```bash
git status
git diff HEAD
git branch --show-current
```

Then:
1. If you are on the default branch (e.g. `main`/`master`), create a feature branch
   first: `git checkout -b <descriptive-branch-name>`.
2. Stage the changes (`git add`) and make ONE commit with an appropriate message.
3. Push the branch: `git push -u origin <branch>`.
4. Open a PR: `gh pr create` with a clear title and body.

Complete all steps, then stop.

## Workflow 3 — Clean gone branches

Remove local branches whose upstream is marked `[gone]` (deleted on the remote),
including any worktrees attached to them. Branches with a `+` prefix have worktrees that
must be removed before the branch can be deleted.

First inspect:

```bash
git branch -v
git worktree list
```

Then run:

```bash
# Process every [gone] branch; strip a leading *, +, or space
git branch -v | grep '\[gone\]' | sed 's/^[+* ]//' | awk '{print $1}' | while read branch; do
  echo "Processing branch: $branch"
  # Remove an associated worktree if one exists (and it isn't the main checkout)
  worktree=$(git worktree list | grep "\[$branch\]" | awk '{print $1}')
  if [ -n "$worktree" ] && [ "$worktree" != "$(git rev-parse --show-toplevel)" ]; then
    echo "  Removing worktree: $worktree"
    git worktree remove --force "$worktree"
  fi
  echo "  Deleting branch: $branch"
  git branch -D "$branch"
done
```

If no branch is marked `[gone]`, report that no cleanup was needed.
