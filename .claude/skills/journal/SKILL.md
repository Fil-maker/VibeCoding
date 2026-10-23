---
name: journal
description: Writes one new journal note for the current change from the decision draft and a digest of every session of the change, through the journal-writer agent, then checks it by script. Use at the end of a change («запиши в журнал», «журнал»), "journal note", or /journal; /finish calls it.
argument-hint: "[task id; optional]"
allowed-tools: Bash(uv run --no-project python .claude/skills/journal/scripts/session_digest.py *) Bash(uv run --no-project python .claude/skills/journal/scripts/check_journal.py *) Bash(uv run --no-project python .claude/skills/document/scripts/session_facts.py *) Bash(git status *) Bash(git log *)
---

You get the journal note of one change written from records, not from memory. Existing notes are never
touched. Talk to the user in Russian; the note is English. Rules: `.claude/rules/docs.md`.

User input (may be empty): $ARGUMENTS

Current state:

!`uv run --no-project python .claude/skills/document/scripts/session_facts.py . session ${CLAUDE_SESSION_ID}`

!`uv run --no-project python .claude/skills/document/scripts/session_facts.py . journal-table`

## 1. Источники

`session_digest.py . --session ${CLAUDE_SESSION_ID}` — the digest of every session of the change (its
path when long). The decisions table is above.

## 2. Заметка

The note path: `docs/journal/YYYY-MM-DD-NN-<slug>.md` (today, NN the next number of the day, the change
slug). Run `journal-writer` with the digest path, the decisions table, the task id, the change name and
the note path.

## 3. Проверка

`check_journal.py . <note>`; read the note against the digest. A failure or a reason without a source →
back to the same `journal-writer` (SendMessage) with what is wrong. Decisions it found in the digest but
not in the draft → ask the user ✋ and record them with `session_facts.py . decide`, then regenerate the
table.

## Never

- Never edit an existing note; a correction is a new note that links to the old one.
- Never write the note yourself.
