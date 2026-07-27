---
name: create-pr
description: Create a GitHub pull request targeting main, with body auto-generated from the diff, using this repo's PR template. Use when the user wants to open a PR from the current branch.
---

Create a pull request for the current branch targeting `main`. Follow these steps exactly:

1. **Gather context** — run these commands in parallel:
   - `git log main..HEAD --oneline` — list commits on this branch
   - `git diff main...HEAD --stat` — summarize changed files
   - `git diff main...HEAD` — full diff (use to understand the changes)
   - `git branch --show-current` — current branch name

2. **Check push status** — run `git status -sb` to see if the branch has an upstream. If no upstream is set, ask the user: "Branch `<name>` hasn't been pushed yet. Push it now?" — wait for confirmation before running `git push -u origin <branch>`.

3. **Detect appropriate labels** — analyze the changes to determine relevant labels:
   - `documentation` — if changes are in `.md` files, `docs/`, or `.github/`
   - `bug` — if commit messages contain "fix", "bug", or "issue"
   - `enhancement` — if new files or features are added
   - `testing` — if changes are in test files or add new tests

4. **Generate PR title** — derive a concise title (under 70 chars) from the commits and diff. Focus on the "what changed at a high level", not implementation details.

5. **Generate PR body** — fill in this repo's template using the git context. Every section must be answered:

```
# What problem did you solve?
<Explain the motivation — the bug, gap, or need this PR addresses. 1-3 sentences.>

# Describe the changes
<Summarize the main code changes. Keep it simple — what was added, removed, or restructured. Bullet points preferred.>

# Testing
<Describe how the changes were tested — unit tests added/run, manual steps taken, CLI commands used.>
```

6. **Create the PR** — run:
```
gh pr create --title "<title>" --base main --label "<label1>" --label "<label2>" --body "$(cat <<'EOF'
<body>
EOF
)"
```
(Include `--label` flags only for detected labels)

7. **Report** — print the PR URL returned by `gh pr create`.
