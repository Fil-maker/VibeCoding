---
name: commit
description: Commits finished work - preflight, docs and journal present, checks and tests green, grouping into Conventional Commits with a Plan footer, explicit staging - after the user agrees. Use when the user wants to commit («закоммить», «коммит»), "commit", or runs /commit; /finish calls it.
argument-hint: "[what to commit; optional]"
allowed-tools: Bash(uv run --no-project python .claude/skills/commit/scripts/preflight.py *) Bash(uv run --no-project python .claude/skills/document/scripts/session_facts.py *) Bash(uv run --no-project python .claude/skills/test/scripts/run_tests.py *) Bash(just check) Bash(git status *) Bash(git diff *) Bash(git log *) Bash(git add *) Bash(git commit -F -)
---

You commit finished work in VibeCoding. Small, finished commits make rollback cheap; the commit gate is
«ask». Talk to the user in Russian; commit messages are English. Rules: `CLAUDE.md` «Workflow».

User input (may be empty): $ARGUMENTS

Current state:

!`uv run --no-project python .claude/skills/commit/scripts/preflight.py .`

!`git status --short`

## How to guide

`**Шаг 2 из 5 · Проверки**` / `Предпроверка → [Проверки] → Группы → Вопрос → Коммит`; «Зачем:» in one
to three sentences, the work, «Дальше:». «без объяснений» drops «Зачем».

## 1. Предпроверка

Зачем: скрипт ловит то, что нельзя коммитить, до того как оно попадёт в историю.

A block in the preflight stops the commit: say what and how to fix it. Unconfirmed decisions → show
`session_facts.py . decisions`, ✋ confirm, `confirm`, `write-decisions`. Docs the changes usually touch
but did not → `/document` or a line why not. A change of a task without its journal note → `/journal`.

## 2. Проверки

Зачем: в main попадает только зелёное.

`just check` and `run_tests.py . auto` (the database suite when the preflight says it is needed). Red →
stop.

## 3. Группы

Group the changes into commits, one finished unit of work each — never split by file type, never a
separate journal or docs commit. Message: `<type>(<scope>): <summary>` (English, imperative, ≤ 72
chars), a body for the non-obvious, footer `Plan: <id>` when a plan task is involved. Types: feat, fix,
refactor, build, ci, docs, chore, test, perf, style, revert; `!` for breaking.

## 4. Вопрос ✋

Show the groups with their files and messages. ✋ «Коммитим?» (skip when `/finish` already asked and the
user said «Да»).

## 5. Коммит

Stage explicitly (`git add <files>`), commit with the message on stdin (`git commit -F -`). A hook that
changed files → review the change, stage again, commit again. Then `session_facts.py . clear`. Report
the hashes. Start `/release` only when the user asks for it.

## Never

- Never `--no-verify`, never `--amend`, never `git add -A` or `.`.
- Never push (only `/release` pushes).
- Never commit `.env`, `.claude/session/` or `.claude/settings.local.json`.
