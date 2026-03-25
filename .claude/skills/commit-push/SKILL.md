---
name: commit-push
description: Commit all staged and unstaged changes with a descriptive message and push to the remote repository. Use when the user says /commit-push or asks to commit and push their changes.
user_invocable: true
---

# Commit and Push

Commit all current changes and push them to the remote repository.

## Instructions

1. Run `git status` to see all changed and untracked files. Never use the `-uall` flag.
2. Run `git diff` and `git diff --staged` to understand what changed.
3. Run `git log --oneline -5` to see recent commit message style.
4. Stage all relevant changed files using `git add` with specific file names. Do not stage files that contain secrets (`.env`, credentials, etc.).
5. Write a clear, concise commit message that describes the "why" of the changes. Follow the existing commit message style from the repo.
6. Create the commit. End the commit message with:
   ```
   Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
   ```
7. Push to the remote repository using `git push`. If the branch has no upstream, use `git push -u origin <branch>`.
8. Report the result to the user (commit hash and push status).
