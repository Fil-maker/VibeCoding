---
name: document
description: Syncs the implementation docs with the changes - plans portions by script, completes the fact sheet, confirms and writes decisions as ADRs, runs doc-writer per portion and doc-checkers per area, then just check. Use after code changes («обнови доки», «документация»), "update docs", or /document; /finish calls it.
argument-hint: "[files or area; optional]"
allowed-tools: Bash(uv run --no-project python .claude/skills/document/scripts/doc_plan.py *) Bash(uv run --no-project python .claude/skills/document/scripts/session_facts.py *) Bash(uv run --no-project python scripts/check_doc_links.py *) Bash(uv run --no-project python scripts/check_doc_facts.py *) Bash(just check) Bash(git status *) Bash(git diff *)
---

You bring the implementation docs of VibeCoding in line with the code. Cheap subagents write and check
docs, so they get a small scope and only facts from the fact sheet and the code. Talk to the user in
Russian; briefs and docs are English. Rules: `.claude/rules/docs.md`, `.claude/rules/docs-sync.md`.

User input (may be empty): $ARGUMENTS

Current state:

!`uv run --no-project python .claude/skills/document/scripts/doc_plan.py . plan`

!`uv run --no-project python .claude/skills/document/scripts/session_facts.py . sheet`

## How to guide

`**Шаг 3 из 6 · Решения**` / `План → Факты → [Решения ✋] → Запись → Проверка → Итог`; «Зачем:» in one to
three sentences, «Дальше:». «без объяснений» drops «Зачем».

## 1. План

«Nothing to document» → say so and stop. Otherwise show the portions (at most 15 files each) and their
docs.

## 2. Факты

Зачем: субагент пишет только из листа фактов; чего нет в листе — того он не угадает.

Complete the fact sheet from this session and the change: `session_facts.py . fact "<text>"` for each
fact a doc needs (what was built, names the reader must know); `keep "<what stays unchanged>"`.

## 3. Решения ✋

Зачем: в ADR попадают только решения, подтверждённые пользователем, его словами.

`session_facts.py . decisions`; ✋ «Подтверждаешь решения?» (drop wrong ones with `drop <n>`). Then
`confirm` and `write-decisions` (it writes `docs/adr/NNNN-<slug>.md` and the `docs/decisions.md` row).

## 4. Запись

One `doc-writer` per portion, one at a time (foreground): the portion's files, the docs and sections,
the output of `session_facts.py . sheet`, the two rules. Then `session_facts.py . check-quotes <pages>`;
an unsourced quote goes back to the same `doc-writer`.

## 5. Проверка

`doc-checker`s in parallel, one per docs area (at most four), one message. Filter their findings against
the code; send confirmed ones to the same `doc-writer` (SendMessage). Then `just check`.

## 6. Итог

Report which docs changed and why, findings fixed, facts that were missing.

## Never

- Never let a subagent write `docs/decisions.md`, ADRs or product docs.
- Never write a reason that is not in the draft.
