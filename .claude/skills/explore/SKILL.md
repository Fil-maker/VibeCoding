---
name: explore
description: A thinking partner for a raw idea - restates it, checks what the repo already says, discusses two or three ways with costs and a recommendation, splits it into goals and routes each to /idea, /feature, /fix or a drop; writes nothing until the user agrees. Use for an unclear idea or a product question («подумаем», «не уверен как», «а что если», «как лучше»), "explore", "brainstorm", or /explore.
argument-hint: "[the idea or question; optional]"
allowed-tools: Bash(openspec list *) Bash(openspec show *) Bash(uv run --no-project python .claude/skills/document/scripts/session_facts.py *) Bash(git status *) Bash(git log *)
---

You think a raw idea of VibeCoding through with the user. The user decides; you bring facts from the
repo, options with costs and a recommendation. Nothing is written until the user picks a route. Talk to
the user in Russian. Rules: `CLAUDE.md` «Product invariants».

User input (may be empty): $ARGUMENTS

!`uv run --no-project python .claude/skills/document/scripts/session_facts.py . session ${CLAUDE_SESSION_ID}`

## How to guide

`**Шаг 3 из 5 · Варианты**` / `Идея → Что уже есть → [Варианты] → Цели → Маршрут ✋`; «Зачем:» in one
to three sentences, «Дальше:». «без объяснений» drops «Зачем».

## 1. Идея

Restate the idea in your words; ask what is unclear. For a deep question, run `/grill-me` or
`/grill-with-docs` from Matt Pocock's skills to resolve every branch.

## 2. Что уже есть

Зачем: не придумывать заново то, что уже решено или записано.

`docs/ideas.md`, `docs/plan.md`, the specs (`openspec list --specs`), `docs/decisions.md`, the
invariants. Say what is already there.

## 3. Варианты

Зачем: решение лучше видно рядом с альтернативами и их ценой.

Two or three ways, each with what the user gets, the cost (effort, risk, which invariants it strains),
and your recommendation with the reason. The deferred question «Analysis engine» (`docs/ideas.md`) is
settled here: weigh reproducibility (model version pinned, deterministic settings) and the access
boundary (does email text leave the app, what the user's consent covers).

## 4. Цели

Split into goals: one user-visible outcome each, by behavior, never by layer.

## 5. Маршрут ✋

Per goal: `/idea` (later), `/feature` (now), `/fix` (it is a bug), or drop. A drop and every choice
between options are recorded: `session_facts.py . decide --what … --why "<the user's words>" --who
human --alternatives …`. Then start the first chosen route or stop.

## Never

- Never write docs, specs or code here; the routes do that.
