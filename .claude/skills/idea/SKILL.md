---
name: idea
description: Records one idea in docs/ideas.md without starting work - checks it is not already there, names the FRs and invariants it touches, drafts the entry and writes it after the user agrees. Use when the user has an idea for later («идея», «запиши на потом», «было бы круто»), "idea", "backlog", or runs /idea.
argument-hint: "[the idea; optional]"
allowed-tools: Bash(openspec list *) Bash(git status *)
---

You record one idea of VibeCoding for later. Nothing is built; the idea is kept so it is not lost and not
started by accident. Talk to the user in Russian; the entry is English (quotes stay as said). Rules:
`.claude/rules/docs.md`.

User input (may be empty): $ARGUMENTS

## How to guide

`**Шаг 2 из 4 · Проверка**` / `Идея → [Проверка] → Запись ✋ → Готово`; «Зачем:» in one to three
sentences, «Дальше:». «без объяснений» drops «Зачем».

## 1. Идея

Restate the idea in one or two sentences; ask once if the what or the why is missing.

## 2. Проверка

Зачем: одна идея — одна запись; дубль или уже запланированная работа не записываются.

Check `docs/ideas.md`, `docs/plan.md` and `docs/prd.md` «Stages and scope». Name the FRs it touches
(`openspec list --specs`, `docs/domain.md` «Requirements map») and the invariants of `CLAUDE.md`
«Product invariants» it touches — touching one marks a new direction. A bug the user wants later goes to
«Technical backlog».

## 3. Запись ✋

Draft the entry under the right area:

```markdown
### <Short name>

Added DD.MM. <What the user or the system does, one to three sentences.> Why: <the problem or metric>.

**Open:** <questions to settle before work; omit when none>.

**Touches:** FR-…, FR-… (<capability>); invariant «…» — a new direction. <Omit when nothing.>
```

✋ «Записываю?». On «да» write it and update the doc's `Updated` date.

## 4. Готово

Say where it is and how it would start: `/explore` to think it through, `/feature` to build it.

## Never

- Never start work on the idea, create a branch or a change.
