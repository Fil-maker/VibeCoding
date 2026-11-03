# Design

## Context

Task 1.6 «Apply a rule now» of `docs/plan.md`; requirements FR-47 (new) and FR-45 modified
(`placement-rules`), FR-46 modified (`chain-placement`). Since task 1.5 a rule places a chain only on a
mailbox read (`place_new_chains`) and on «Заполнить», both in `projects`, both under the lock of all
the user's projects, through `projects/rule_placing.py`. The `rules` module owns rule CRUD; `projects`
reaches it only through `rules.service` (ADR 0067). A placement is one row of `chain_placements` per
chain with the kind `engine`, `manual`, `excluded` or `rule`; a `rule` row keeps its own copy of the
rule's condition and value. A move by hand deletes a thread left empty
(`delete_thread_if_empty_for_owner`).

The user decided (session decisions 2–5): changed behavior, `feat`; an applied rule may move chains in
no project, placed by the engine or by a rule, never by hand or taken out; the page lists the moves and
nothing moves without «Применить»; a chain moves only when the applied rule is its winning rule.

## Goals / Non-Goals

Goals:
- After a rule is saved, show the exact chains it would move, from where to where.
- Move them on confirmation, by the same matching, priority and thread-by-name as a fill.
- Never move a chain placed by hand or taken out, nor one the user did not see in the list.

Non-Goals:
- Applying a rule later from the list, or several rules at once (`docs/ideas.md` «Apply a rule later»).
- Any change to the fill, the new-chain placement, the matching or the explanations.
- A schema change.

## Decisions

### The moves live in `projects`

Listing and applying the moves read and write placements and threads, which `projects` owns; the rule
itself comes from `rules.service` through a new read `get_match_rule(session, user_id, rule_id)`, so the
import direction of ADR 0067 stays (`projects` → `rules.service`). A new file
`projects/rule_applying.py` holds the use case; `ProjectsService` gains two methods; the routes join
`placements_router` (`/api/v1/placements`, tag `projects`). Alternative: routes in the `rules` module
with the placement passed in through `ProjectDirectory` — rejected, it would carry placement writes
through a callback across modules.

### Which chains a rule moves

A chain of the user is a move of rule R when all hold:
- its placement is none (no row), `engine` or `rule` — never `manual` or `excluded`;
- the winning rule among all the user's rules (FR-46 priority) for its senders and first subject is R;
- it is not already in place: its project is R's project and its thread is the one R names (the first
  thread by position whose stripped, case-folded name equals R's thread name), or both are
  «Неразобранное».

A chain already in place keeps its placement and explanation, whatever its kind. Alternative: relabel
such a chain to «Правило» — rejected, it would list «X → X» lines that move nothing.

### List, then apply what the user saw

`GET` computes the moves without writing. `POST` takes the chain ids the user saw, locks the user's
projects (as a fill does), computes the moves again, and moves only the ids that are both in the body
and still moves now; ids of other users' chains, unknown ids and chains no longer qualifying are skipped
silently. So a chain moved by hand, taken out or claimed by a stronger rule between the list and
«Применить» stays, and a second identical `POST` moves nothing (FR-47 «Applied twice»).
Alternative: apply recomputes with no body — rejected, it could move chains the user never saw.

### One move

For each chain to move, in the order of the list: delete its current placement row (if any), place it
by R through the existing rule placement (thread found by name or created, the rule copied into the
row, `placed_at` now), then delete its former thread if it is now empty. The former placement is gone,
as on filling again; the history of the emails is untouched.

### Who may do what

Both routes need a signed-in user; `POST` also a matching `Origin`. R must be the caller's rule (else
404 `not_found`); every chain read and written is filtered by the caller's id.

## Interface

Paths under `/api/v1`; 401 `not_signed_in` without a session, 403 `forbidden_origin` on `POST` from
another site; another user's rule id answers 404 `not_found`.

### Schemas

- `RuleMoveSource`: `{state: "none" | "placed", project: ProjectRef | null, thread: ThreadSummary | null}`
  — `"none"` with both null; `"placed"` with a project and a thread or null for «Неразобранное».
- `RuleMoveTarget`: `{project: ProjectRef, thread_name: str | null}` — null for «Неразобранное»; the
  name as written in the rule.
- `RuleMove`: `{chain_id: uuid, subject: str, latest_email_at: datetime, current: RuleMoveSource, target: RuleMoveTarget}`.
- `RuleMoves`: `{moves: RuleMove[]}` — newest `latest_email_at` first, then by `chain_id`.
- `RuleApply` (request): `{chain_ids: uuid[]}` — 0 to 5000 ids, duplicates ignored.
- `RuleApplied`: `{moved: int}`.

### Routes

| Route | Body | Success | Errors |
|---|---|---|---|
| `GET /placements/by-rule/{rule_id}` | — | 200 `RuleMoves` | 404 `not_found` |
| `POST /placements/by-rule/{rule_id}` | `RuleApply` | 200 `RuleApplied` | 404 `not_found`, 422 `validation_failed` |

### Python

- `rules.service.get_match_rule(session, user_id, rule_id) -> MatchRule | None` — the user's rule for
  matching, `None` for an unknown or another user's id; in the caller's transaction.
- `ProjectsService.list_rule_moves(context, rule_id) -> RuleMoves` and
  `ProjectsService.apply_rule(context, clock, rule_id, body: RuleApply) -> RuleApplied`; `NotFound` for
  a rule that is not the caller's.

### SPA (page «Правила»)

- After «Создать правило» or «Сохранить» succeeds, the page fetches the moves of that rule and shows a
  panel «Применить правило сейчас?» listing each move as «<subject>: <откуда> → <куда>», where
  «откуда» is «Вне проектов», «<project> → Неразобранное» or «<project> → <thread>», and «куда» is
  «<project> → <thread name>» or «<project> → Неразобранное»; buttons «Применить» and «Не сейчас».
- With no moves the panel shows «Подходящих цепочек нет» and a button «Понятно».
- «Применить» sends the listed ids and then shows «Перемещено цепочек: <N>»; «Не сейчас» closes the
  panel and sends nothing. While a request runs, the buttons are disabled.

### Test seams

- As in task 1.5: the HTTP API with `FakePlacementEngine`; projects, placements by hand, rules and
  chains through `backend/tests/factories.py` and `backend/tests/mail_factory.py`. No new factory: no
  column is added.
- The SPA panel through component tests of the rules page with a mocked client.

## Risks / Trade-offs

- A broad rule may list hundreds of chains → the list shows them all, scrollable; the user sees the
  scale before pressing «Применить».
- Computing the moves reads all the user's chains and rules → the same read a fill does; one rule at a
  time, on the user's action only.
- «Не сейчас» leaves no way to apply that rule later but saving it again or «Заполнить» → accepted for
  this task; «Apply a rule later» goes to `docs/ideas.md`.

## Migration Plan

No schema change. The backend and the SPA ship together; the regenerated client knows the new routes.
Rollback is the previous release; placements made by an applied rule are ordinary `rule` rows.
