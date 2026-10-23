---
name: release
description: Makes a release - computes the next SemVer from Conventional Commits, checks preconditions, drafts the CHANGELOG section and the release note for approval, bumps the version, commits, tags and pushes. Run only by the user with /release.
argument-hint: "[explicit version X.Y.Z; optional]"
disable-model-invocation: true
allowed-tools: Bash(uv run --no-project python .claude/skills/release/scripts/next_version.py *) Bash(just check) Bash(git status *) Bash(git log *) Bash(git fetch *) Bash(git add *) Bash(git commit -F -) Bash(git tag -a *) Bash(git push *)
---

You release VibeCoding. A release is for the product's users: the CHANGELOG and the notes speak their
language. Talk to the user in Russian; the CHANGELOG and notes are English. Rules:
`.claude/rules/versioning.md`.

User input (may be empty): $ARGUMENTS

Current state:

!`uv run --no-project python .claude/skills/release/scripts/next_version.py .`

!`git status --short --branch`

## 1. Версия

«Nothing to release» → say so and stop. No tag yet → propose `0.1.0` ✋. An explicit version from the
input overrides; `1.0.0` only when the user says so.

## 2. Предусловия

On `main`, clean tree, `git fetch` and not behind `origin/main`, `just check` green. A failure stops the
release. Pushing needs a GitHub remote with access: if `git push` cannot authenticate, tell the user to
sign in (Git Credential Manager or `gh auth login`) — never handle a token yourself.

## 3. Черновик ✋

The CHANGELOG section `## [X.Y.Z] - YYYY-MM-DD` with Keep a Changelog headings, for users, from the
grouped commits; the note `docs/releases/vX.Y.Z.md` with «What's new», «Fixes», «Breaking changes»,
«Under the hood», «How to update» only when action is needed; a row in `docs/releases/README.md`. ✋
«Выпускаем?».

## 4. Выпуск

Bump `version` in the root `pyproject.toml` (the one source), stage the three files explicitly, commit
`chore(release): vX.Y.Z` (`git commit -F -`), `git tag -a vX.Y.Z -m "vX.Y.Z"`, `git push origin main
--follow-tags`. Report the tag and remind the user that deploys are manual.

## Never

- Never release from a branch other than `main` or with red checks.
- Never edit a published release note.
