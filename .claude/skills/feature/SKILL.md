---
name: feature
description: Leads one product change from the idea to the release - triage, exploration, plan row, OpenSpec change with delta specs, approval, code by subagents with tests in a sandbox, finish - and resumes an unfinished change from its state. Use when the user wants to add or change behavior («хочу добавить», «новая фича», «давай сделаем», «продолжи задачу»), "new feature", "implement task 1.2", or runs /feature.
argument-hint: "[task id, change name or a short description; optional]"
allowed-tools: Bash(uv run --no-project python .claude/skills/feature/scripts/change_state.py *) Bash(uv run --no-project python .claude/skills/feature/scripts/tdd_sandbox.py *) Bash(uv run --no-project python .claude/skills/document/scripts/session_facts.py *) Bash(openspec *) Bash(git status *) Bash(git diff *) Bash(git log *) Bash(git switch *) Bash(git branch *) Bash(git fetch *)
---

You lead one change of VibeCoding through spec-driven development. The user decides scope, requirements
and approvals (✋); you explore, draft, orchestrate subagents and review. Talk to the user in Russian;
artifacts, briefs and reports are English. Rules: `CLAUDE.md` «Workflow», `.claude/rules/docs.md`.

User input (may be empty): $ARGUMENTS

Current state:

!`uv run --no-project python .claude/skills/feature/scripts/change_state.py .`

!`uv run --no-project python .claude/skills/document/scripts/session_facts.py . session ${CLAUDE_SESSION_ID}`

## How to guide

Each step opens with a header and the route, the current step in brackets:
`**Шаг 3 из 7 · План**` / `Разбор → Исследование → [План] → Изменение → Одобрение → Код → Финиш`.
Then «Зачем:» in one to three sentences about this change, then the work, then «Дальше:». ✋ steps end
with AskUserQuestion (recommended option first, marked «(рекомендую)») and wait. After «без объяснений»
drop «Зачем» for the rest of the session. Record every decision the user makes at once:
`session_facts.py . decide --what "…" --why "<the user's words>" --who human [--alternatives "…"]`.

## 0. Resume or start

From the state: a change in progress → `git switch` to its expected branch and resume at its stage
(approved → step 6 in this session if it is fresh, else say «/clear, затем `/feature`»; code done → say
«/clear, затем `/finish <id>`»). One change is implemented at a time, at most one more in design without
a branch. Otherwise start at step 1. Record the task: `session_facts.py . task <id>`.

## 1. Разбор ✋

Зачем: путь определяет, нужны ли дельты спек, сколько сессий и какой будет коммит.

Pick the path with the user:

| Path | Spec change | Commit and version |
|---|---|---|
| New capability | ADDED, plus MODIFIED of neighbours it touches | `feat` → minor |
| Changed behavior | MODIFIED; a vanishing scenario → REMOVED + ADDED with a new number | `feat`, breaking `feat!` |
| Removed capability | REMOVED; `retire_capabilities` | `feat!` |
| Bug | → `/fix` | `fix` → patch |
| Non-functional | MODIFIED in security, operations, retention | `feat` or `fix` |
| Technical, same behavior | `skip_specs: true`, no `specs/` | `refactor`, `build`, `ci` — no release |
| Minor (typo, an hour of refactoring) | none, no plan row, one session, straight to the code | by type |
| New direction (touches an invariant) | the decision, `docs/prd.md` and the invariants first; design mandatory | `feat` or `feat!` |

## 2. Исследование

Зачем: дельта, написанная по догадке, ломает соседние требования.

Read, do not guess: the code it touches, the capabilities and FRs (`openspec list --specs`,
`openspec show <capability> --type spec`) and neighbours needing MODIFIED, `CLAUDE.md` «Product
invariants», the size. For an unclear idea run `/grill-with-docs` (or `/grill-me`) from Matt Pocock's
skills; never `/to-spec` or `/to-tickets`. Split when parts ship on their own value, carry different risk
or do not fit two sessions. All open questions in one AskUserQuestion.

## 3. План ✋

Зачем: строка плана с «Done when» — это то, по чему `/finish` примет задачу.

Draft the `docs/plan.md` row (next task id from the state; FR «—»; «Done when» in checkable sentences,
each ending with a period). ✋ «Записываю строку плана?»; on «да» add it and bump the plan edition.

## 4. Изменение

Зачем: предложение, дельты, дизайн и задачи фиксируют поведение до кода.

Branch first: `git switch -c <type>/<change>` from an up-to-date `main`; name foreign uncommitted files
to the user. `openspec new change <change>`; then for each artifact in order (proposal, specs, design,
tasks) run `openspec instructions <artifact> --change <change>` and write it from that template. Read
[delta-rules.md](delta-rules.md) before the specs. Take FR numbers from the state («next FR»). Design
gets «Interface» when there is code with scenarios. Large or uncertain: ✋ after the proposal.

## 5. Одобрение ✋

Зачем: код пишется только по одобренным дельтам.

Run `openspec validate <change> --strict`, go through the checklist below and fix what fails. Show: the
proposal in a few lines, every delta requirement in full (for MODIFIED: what changed), design decisions
with alternatives, the interface, the task groups. ✋ «Одобряем дельты?». On «да»: record the decision,
fill the plan row's FR, write `openspec/changes/<change>/handoff.md` (template in
[code-step.md](code-step.md) «Handoff») with `- Approved: <YYYY-MM-DD>`, say «/clear (или новая
сессия), затем `/feature`» and stop.

Checklist:
- **proposal:** «Why» is a user problem from `docs/prd.md`; out of scope listed, deferred items in
  `docs/ideas.md`; touched invariants named (or «none»).
- **specs:** SHALL/MUST; concrete scenarios with negative cases (another employee's correspondence, an
  employee versus the administrator, missing consent); MODIFIED carries the whole requirement;
  validation passes.
- **design:** alternatives and reasons; existing data survives the migration, rollback clear; who may
  call each action and whose data it touches; no new services without asking; «Interface» holds only
  the public contract.
- **tasks:** every task ends with «check — …»; test tasks for `test-writer` in the sandbox and manual
  flow checks where tests cannot reach; factories named when a column is added; a «Verification» group;
  the plan row's «Done when» as the last group.

## 6. Код

Зачем: тесты пишутся из сценариев в песочнице, код — отдельным агентом; так тесты проверяют спеку.

In a fresh session: read [code-step.md](code-step.md) now and follow it. A disagreement between code and
a delta stops the work: the delta is edited and re-approved. Anything outside the change goes to `/idea`
or `/fix`; the change does not grow. Ends with `- Code done:` in the handoff and «/clear, затем
`/finish <id>`».

## 7. Финиш

In a fresh session: `/finish`.

## Never

- Never write code before the deltas are approved; never `/opsx:sync` deltas into the specs before the
  code exists.
- Never write product code or tests yourself in a Standard/Full change; delegate and review.
- Never commit here; `/finish` does it through `/commit`.
