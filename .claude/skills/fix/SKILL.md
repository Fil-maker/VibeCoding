---
name: fix
description: Leads one bug from the symptom to the patch - reproduction, diagnosis against the spec, a spec scenario when the spec is silent, a failing test, the root-cause fix by subagents, then /finish. Use when something works wrong («баг», «не работает», «сломалось», «ошибка»), "bug", "fix", or the user runs /fix.
argument-hint: "[what is wrong; optional]"
allowed-tools: Bash(uv run --no-project python .claude/skills/feature/scripts/change_state.py *) Bash(uv run --no-project python .claude/skills/feature/scripts/tdd_sandbox.py *) Bash(uv run --no-project python .claude/skills/document/scripts/session_facts.py *) Bash(uv run --no-project python .claude/skills/test/scripts/run_tests.py *) Bash(openspec *) Bash(git status *) Bash(git diff *) Bash(git log *) Bash(git switch *) Bash(git branch *) Bash(git grep *)
---

You lead one bug fix of VibeCoding. The user confirms the diagnosis and any spec change (✋); you
reproduce, diagnose and orchestrate subagents. Talk to the user in Russian; artifacts, briefs and
reports are English. Rules: `CLAUDE.md` «Workflow», `.claude/rules/testing.md`.

User input (may be empty): $ARGUMENTS

Current state:

!`uv run --no-project python .claude/skills/feature/scripts/change_state.py .`

!`uv run --no-project python .claude/skills/document/scripts/session_facts.py . session ${CLAUDE_SESSION_ID}`

## How to guide

Step header and route: `**Шаг 2 из 6 · Воспроизведение**` /
`Симптом → [Воспроизведение] → Диагноз → Спека → Тест и фикс → Финиш`; «Зачем:» in one to three
sentences, the work, «Дальше:». ✋ steps end with AskUserQuestion and wait. «без объяснений» drops
«Зачем». Decisions go to `session_facts.py . decide … --who human` at once.

## 1. Симптом

Зачем: без точного симптома легко починить не то.

What happens, what was expected, where, the steps with data, since when. Ask once for what is missing.

## 2. Воспроизведение

Зачем: фикс по догадке не доказывает, что баг ушёл.

Reproduce on the dev server (in the built-in browser), with a test, or by reading the pure logic. Never
fix by guess. The reproduction steps become the manual check. Matt Pocock's `diagnosing-bugs` skill may
lead steps 2–3.

## 3. Диагноз ✋

Зачем: диагноз по спеке решает, баг ли это и нужна ли новая сцена.

Find the covering requirement (`openspec show <capability> --type spec`) and the root cause, and why the
checks missed it; `git grep` for the same mistake elsewhere. Cases:
- **A** the code breaks a scenario → fix without a spec change;
- **B** the spec is silent → a change `fix-<slug>` adds the scenario first;
- **C** the spec describes exactly this → not a bug: hand over to `/feature`;
- **D** not product behavior (tooling, build, docs) → no spec, no `test-writer`.

Spoiled stored data (wrong assessments saved) → ✋ whether and how to repair it (a migration or a
recomputation). ✋ «Диагноз верный?».

## 4. Спека ✋ (only B)

Зачем: сначала сценарий в спеке, потом тест и код.

`git switch -c fix/<slug>`; `openspec new change fix-<slug>`; MODIFIED of the covering requirement with
the new scenario (whole requirement, `.claude/skills/feature/delta-rules.md`), or ADDED with the next FR
number. Validate `--strict`. ✋ «Одобряем сценарий?».

## 5. Тест и фикс

Зачем: падающий тест фиксирует баг, а исправление причины — а не симптома — не даёт ему вернуться.

On `fix/<slug>`: follow `.claude/skills/feature/code-step.md` with one scenario. `code-writer` gets the
root cause and «the smallest change that removes it; no refactoring along the way; fix or name the same
mistake elsewhere». The test lives at the lowest layer that shows the bug and names the FR. Case D:
`code-writer` alone, test when the tooling has tests. Handoff (in the change, or
`.claude/session/handoff-fix-<slug>.md`), then «/clear, затем `/finish`».

## 6. Финиш

`/finish`: `fix` → patch release; tooling fixes get their own type (`build`, `ci`, `chore`) and no
release. The summary names the cause, the test that now guards it and the check that was missing.

## Never

- Never weaken a test or a check to make the bug disappear.
- Never refactor along the way; ideas go to `/idea`.
