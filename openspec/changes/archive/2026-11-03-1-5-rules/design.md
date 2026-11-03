# Design

## Context

Task 1.5 «Rules» of `docs/plan.md`; requirements FR-43…FR-45 (`placement-rules`) and FR-46 with
FR-35, FR-36, FR-37, FR-39, FR-42 modified (`chain-placement`). After task 1.4 a chain's placement is
one row of `chain_placements` with the kind `engine`, `manual` or `excluded`; the fill
(`ProjectsService.fill`) and the new-chain placement (`place_new_chains`, run in the mailbox batch) both
take the chains with no placement row, score them with the engine and write through `Placer`, under the
lock of all the user's projects. The model already notes that task 1.5 adds a kind «by a rule».

The user decided (session decisions 1–4): a new capability for rules; the more specific rule wins
(address, domain, subject words; then the one created first); rules apply on «Заполнить» before the
engine and filling again recomputes the placements by rules of that project; a rule targets a project
and a thread by name, found or created, with no name meaning «Неразобранное».

## Goals / Non-Goals

Goals:
- Rules the user creates, lists, edits and deletes, each targeting one of their projects.
- Rules place new chains before the engine and the fill's candidates before the engine, by one
  deterministic priority.
- A placement by a rule explains itself by the rule as it was, survives the rule's edit or deletion, and
  ranks between the hand's and the engine's on a merge.

Non-Goals:
- Applying a rule at once to chains already in no project; rules by recipient or body; «or»/«not»;
  manual ordering; a rule from a chain's page (all to `docs/ideas.md`).
- Moving any placed chain when a rule is created, edited or deleted.

## Decisions

### Rules live in the `projects` module

A rule targets a project and is read by the fill and the new-chain placement, both in `projects`; a
separate `rules` module would need `projects.service` to check the target, and `projects.service` would
need the rules to place chains — an import cycle. The rules get their own files inside `projects`
(use cases and pure matching apart from the existing placement files), so no file grows past the limit.
Alternative: a `rules` module with the matching passed in as a callback — rejected, it splits one
placement policy across two modules for no gain.

### Matching and priority are pure

A pure function takes the rules in priority order and a chain's senders and first subject and returns
the winning rule or none:
- address: equal to one of the chain's sender addresses, both in lower case;
- domain: a sender's part after «@» equals the domain or ends with «.» + the domain;
- subject words: the rule's value and the subject are lower-cased, «ё» read as «е», split on anything
  that is not a letter or a digit; every rule word must be the beginning of some subject word.
Priority is the total order (kind: address, domain, subject; `created_at`; `id`), the same order the
list shows (FR-44), so a placement never depends on the order rules or emails were read in (FR-38).
Alternative for subject words: substring — rejected, «акт» would match «контакт».

### Senders of a chain

`correspondence` already gives `ChainDocument` per chain for the engine; it gains `senders`, the
distinct lower-cased `from_address` values of the chain's emails, sorted. One read serves rules and
engine. The user's own addresses are not removed: a rule by the user's own address is the user's choice.

### Thread by name

The rule keeps `thread_name` (null for «Неразобранное»). Placing by a rule looks for the project's first
thread by position whose name, stripped and case-folded, equals the rule's; when none exists it creates
one named as written in the rule, at the next position. A thread emptied by the user or by filling
again disappears as in task 1.4, and the next placement by the rule recreates it. Alternative: a reference to a thread id — rejected by the user (decision 4).

### A placement by a rule keeps the rule as it was

A `rule` placement row stores `rule_condition` and `rule_value` copied from the rule at placing time.
The explanation (FR-37) reads them, so an edit or a deletion of the rule never changes what a placed
chain shows, and no foreign key ties placements to rules. Alternative: a `rule_id` with the text read
live — rejected, it would rewrite the reason of past placements (invariant «Explainable placement»).

### New chains (FR-39, FR-46)

`place_new_chains` keeps its candidates (chains in `chain_ids` with no placement row). It reads the
user's rules in priority order; each candidate, in reading order, with a winning rule is placed by it
into the rule's project, filled or not. The rest go to the engine exactly as before; the engine's
thread states are read after the rule placements, so a rule's thread counts as an existing thread.

### Fill and filling again (FR-35, FR-36)

Under the same lock: delete the project's `engine` and `rule` rows and the threads holding no `manual`
row; take the chains with no placement row; for each, in reading order, the winning rule decides — this
project: placed by the rule; another project: left out; none: an engine candidate. Rule placements are
written first, then the engine scores its candidates and `Placer` places them with thread states that
include the rule threads. An edited rule therefore takes effect on filling its project again; a chain
whose rule now targets another project stays in no project until that project is filled or the chain
gets a new email.

### Merging chains (FR-42)

`carry_placement_for_owner` ranks `manual` and `excluded` 0, `rule` 1, `engine` 2, then keeps the
existing tie-breaks (earliest `placed_at`, project created first, name, thread position).

### Data model (revision `0007`)

New table `placement_rules`: `id`, `user_id` (→ users, cascade), `condition` (`address`, `domain`,
`subject`, checked), `value` text, `project_id` (→ projects, cascade), `thread_name` text null,
`created_at`, `updated_at`; a unique index on (`user_id`, `condition`, `lower(value)`) backs «Такое
правило уже есть»; an index on `user_id`.

`chain_placements` gains `rule_condition` and `rule_value`, both nullable; the check `kind` becomes
`kind in ('engine', 'manual', 'excluded', 'rule')`; the check `shape` gains `rule` — project set,
similarity and version null, both rule columns set — and requires both rule columns null for the other
kinds.

Existing rows are `engine`, `manual` or `excluded` with null rule columns, so they pass the new checks
untouched. Downgrade to `0006` deletes the `rule` rows (those chains become «in no project»), restores
the old checks, drops the two columns and the table; everything else survives.

### Who may do what

Every route needs a signed-in user. A rule is read, changed or deleted only by its owner; its target
project must be the caller's, checked under the owner filter (another user's id answers «not found»).
Rules of a user are read only for that user's chains, in that user's fill or mailbox batch. Rule writes
do not take the projects lock: they change no placement.

## Interface

Paths are under `/api/v1`; every route needs a signed-in user (else 401 `not_signed_in`);
state-changing routes need a matching `Origin` (else 403 `forbidden_origin`). Another user's id answers
404 `not_found`.

### Schemas

- `RuleCondition`: `"address" | "domain" | "subject"`.
- `RuleInput` (request): `{condition: RuleCondition, value: str, project_id: uuid, thread_name: str | null}`
  — `value` stripped; address: a valid email address, kept lower-cased; domain: letters, digits and
  hyphens in two or more labels separated by «.», no «@», kept lower-cased; subject: 1–200 characters,
  inner runs of spaces collapsed; `thread_name` stripped, empty becomes null, at most 100 characters.
- `Rule`: `{id: uuid, condition: RuleCondition, value: str, project: {id: uuid, name: str}, thread_name: str | null}`.
- `Placement` (changed): `{kind: "engine" | "manual" | "rule", engine_version: str | null, similarity: float | null, rule: {condition: RuleCondition, value: str} | null}`
  — `engine_version` and `similarity` set exactly when `kind` is `"engine"`; `rule` set exactly when
  `kind` is `"rule"`. It appears in the project tree and in `ChainLocation`.

### Matching (pure, `app.modules.projects.rule_matching`)

- `RuleCondition` (in `app.modules.projects.schemas`): a `StrEnum` with `ADDRESS = "address"`,
  `DOMAIN = "domain"`, `SUBJECT = "subject"`.
- `MatchRule`: a frozen dataclass `{id: UUID, condition: RuleCondition, value: str, project_id: UUID,
  thread_name: str | None, created_at: datetime}`; `value` as stored (normalised per `RuleInput`).
- `winning_rule(rules: Sequence[MatchRule], senders: Sequence[str], subject: str) -> MatchRule | None`
  — the first matching rule in priority order, whatever order `rules` come in; `senders` are the
  chain's sender addresses, `subject` the subject of its first email.

### Routes

| Route | Body | Success | Errors |
|---|---|---|---|
| `GET /rules` | — | 200 `Rule[]` in priority order | — |
| `POST /rules` | `RuleInput` | 201 `Rule` | 404 `not_found`, 409 `rule_exists`, 409 `too_many_rules`, 422 `validation_failed` |
| `PUT /rules/{rule_id}` | `RuleInput` | 200 `Rule` | 404 `not_found`, 409 `rule_exists`, 422 `validation_failed` |
| `DELETE /rules/{rule_id}` | — | 204 | 404 `not_found` |

`POST /projects/{id}/fill`, `GET /projects/{id}` and `GET /placements/{chain_id}` keep their paths;
their `Placement` follows the changed schema.

### Error messages (Russian, exact)

| Code | Message |
|---|---|
| `rule_exists` | «Такое правило уже есть» |
| `too_many_rules` | «Правил не может быть больше 200» |
| field messages | «Укажите адрес почты», «Укажите домен, например stroymaster.example», «Укажите слова темы», «Слова темы — не длиннее 200 символов», «Название ветки — не длиннее 100 символов», «Выберите проект» |

### SPA

- Header: a link «Правила» to `/rules` beside «Проекты».
- Page `/rules` «Правила»: the form with select «Условие» («Адрес отправителя», «Домен», «Слова
  темы»), field «Значение», select «Проект» (the user's projects, first option «Выберите проект»), field
  «Ветка» (placeholder «Неразобранное»), button «Создать правило». Below, the rules in the order of
  `GET /rules`, each as «<Условие>: <value> → <project> → <thread or Неразобранное>» with «Изменить»
  (the same form in place, «Сохранить» and «Отмена») and «Удалить» (the confirmation «Удалить правило?
  Цепочки, уже размещённые им, останутся на месте» with «Удалить» and «Отмена»). No rules: «Правил пока
  нет». No projects: the form is replaced by «Сначала создайте проект» linking to `/projects/new`.
- Explanation of a placement (tree and chain page): «Правило · адрес <value>», «Правило · домен
  <value>», «Правило · слова темы «<value>»»; «Вручную» and «Движок <version> · сходство <N>%» as before.

### Test seams

- As in tasks 1.3–1.4: `get_placement_engine` → `FakePlacementEngine`; `read_due_mailboxes(...,
  engine=...)` with `FakeMailReader`; raw emails from `backend/tests/mail_factory.py`; projects and
  placements by hand through `backend/tests/factories.py`. New factory helper: create a rule through
  the API.
- The pure matching function is tested directly as a unit (priority, domain and subdomain, word
  beginnings, «ё»).

## Risks / Trade-offs

- A broad subject rule («счёт») may claim many chains → the list shows rules in their winning order and
  every placement names its rule; the user deletes or narrows it and fills again.
- A rule into an unfilled project places chains there before the user fills it → the user asked for that
  project by name; FR-39 says so.
- After a rule is retargeted, its old chains stay until the old project is filled again, and then may
  sit in no project until the new one is filled → explicit by design (decision 3); «Apply a rule now»
  goes to `docs/ideas.md`.
- Senders are read for every chain on each fill and batch → the same query that builds documents;
  no new pass.

## Migration Plan

Revision `0007` upgrades in one step with no data rewrite; downgrade to `0006` as in «Data model».
The backend and the SPA ship together (one image set, `just dev`); the regenerated client knows the
kind `rule`.
