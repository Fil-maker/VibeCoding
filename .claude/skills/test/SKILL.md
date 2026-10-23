---
name: test
description: Runs the test suites by script (unit, database, all, auto) and acts on the result - reports counts, finds the cause of a failure and fixes only this session's work, explains a missing environment in plain words. Use when the user wants to run tests («прогони тесты», «тесты»), "run tests", or /test.
argument-hint: "[auto|unit|db|all] [filter]"
allowed-tools: Bash(uv run --no-project python .claude/skills/test/scripts/run_tests.py *) Bash(docker compose *) Bash(git status *) Bash(git diff *)
---

You run the tests of VibeCoding and act on the result. Talk to the user in Russian. Rules:
`.claude/rules/testing.md`.

User input (may be empty): $ARGUMENTS

## 1. Прогон

`run_tests.py . <suite> [filter]` with the suite from the input (default `auto`). Full logs are in
`.cache/tests/<suite>.log`.

## 2. Результат

- **Exit 0:** report the counts per suite. A suite marked NOT PRESENT is reported as absent, never as
  passed.
- **Exit 1:** for each failing test, find the cause from the error and the code. A failure in this
  session's work → fix it (through `code-writer` when the change is delegated), rerun the narrow filter,
  then the full suite. A failure outside this session's work → report it and propose `/fix` or a
  `docs/tech-debt.md` entry.
- **Exit 2:** say in plain words what is missing (Docker not running, `.env` without
  `TEST_DATABASE_URL`, the database not ready) and how to fix it. Never report the skipped suite as passed.

## Never

- Never skip, xfail, loosen or delete a test to make it pass.
