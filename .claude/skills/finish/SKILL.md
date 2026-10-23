---
name: finish
description: Closes a task end to end in a fresh session - checks, acceptance by «Done when», invariant review, OpenSpec archive, docs, journal, then commit and fast-forward merge after the user agrees. Use when the code of a change is done («заканчиваем», «закрой задачу», «финиш»), "finish task 1.2", or the user runs /finish.
argument-hint: "[task id or change name; optional]"
allowed-tools: Bash(uv run --no-project python .claude/skills/feature/scripts/change_state.py *) Bash(uv run --no-project python .claude/skills/finish/scripts/task_card.py *) Bash(uv run --no-project python .claude/skills/document/scripts/session_facts.py *) Bash(uv run --no-project python .claude/skills/test/scripts/run_tests.py *) Bash(uv run --no-project python .claude/skills/journal/scripts/check_journal.py *) Bash(just check) Bash(openspec *) Bash(git status *) Bash(git diff *) Bash(git log *) Bash(git switch *) Bash(git merge --ff-only *) Bash(git branch -d *) Bash(git rebase main)
---

You close one change of VibeCoding. Each step must pass before the next; a failed step stops the run
with a report. The user agrees to the commit (✋). Talk to the user in Russian; briefs and reports are
English. Rules: `CLAUDE.md` «Workflow».

User input (may be empty): $ARGUMENTS

Current state:

!`uv run --no-project python .claude/skills/feature/scripts/change_state.py .`

!`git status --short`

!`uv run --no-project python .claude/skills/document/scripts/session_facts.py . session ${CLAUDE_SESSION_ID}`

## How to guide

`**Шаг 4 из 9 · Ревью**` / `Что закрываем → Проверки → Done when → [Ревью] → Спека → Доки → Журнал →
Вопрос → Коммит`; «Зачем:» in one to three sentences, the work, «Дальше:». «без объяснений» drops «Зачем».

## 1. Что закрываем

Зачем: финиш работает только с готовым кодом на своей ветке.

The branch (code on `main` → offer a branch); the handoff (no `- Code done:` → back to `/feature` or
`/fix`); the task card `task_card.py . <id>`; the change; `git diff --stat main...HEAD`; open questions
from the handoff.

## 2. Проверки

Зачем: ничего не принимается на красных проверках.

`just check`; `/test` (`run_tests.py . auto`). When a model changed: Alembic autogenerate must report no
changes (`uv run --directory backend alembic check`). A failure → `code-writer` with the output, then
this step again.

## 3. Done when

Зачем: задача принята, когда пользователь увидит то, что обещано в плане.

Each «Done when» item of the task card → its covering test, a `flow-checker` verdict, or a manual step
for the user. An unmet item stops the run.

## 4. Ревью

Зачем: инварианты продукта ломаются тихо, поэтому весь диф читается по правилам.

`invariant-reviewer` on `main...HEAD` plus uncommitted changes. A finding that holds against its rule →
`code-writer`, then step 2 again; a false one is dropped with a line why.

## 5. Спека

Зачем: архив вливает дельты в спеки, и спеки снова описывают то, что построено.

All tasks of the change ticked; `openspec validate <change> --strict`; deltas match what was built;
delete the handoff; `openspec archive <change> --yes` (`--skip-specs` for a technical change); update
`docs/domain.md` «Requirements map» and its `Last FR number:` line; propose the product-doc edits
(`docs/domain.md` explanations, `docs/prd.md` stage ✅, `docs/plan.md` row → «Done») as diffs for
step 8.

## 6. Доки

`/document`.

## 7. Журнал

`/journal`, then `check_journal.py . <note>` and read the note against its sources.

## 8. Вопрос ✋

Show: what was done, with check, test and review counts; the manual steps for the user; the product-doc
edits as diffs; open questions with recommendations; what goes into the commit. ✋ «Коммитим и вливаем в
main?» — «Да» · «Только коммит в ветке» · «Пока нет».

## 9. Коммит, слияние, релиз

`/commit`. When `main` moved ahead: `git rebase main` and repeat step 2. Then `git switch main`,
`git merge --ff-only <branch>`, `git branch -d <branch>`. `/release` when a `feat` or `fix` landed and
the user wants a release. Report hashes, the merge, the release and what is next.

## Never

- Never skip a step or report a skipped database suite as passed.
- Never fix code yourself; findings go to `code-writer`.
- Never merge without fast-forward or push here (only `/release` pushes).
