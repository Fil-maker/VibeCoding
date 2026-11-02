# Design

## Context

Task 1.3 built the `projects` module: `projects`, `threads` and `chain_placements` (one row per chain,
primary key `chain_id`, `kind` checked to `'engine'`, `similarity` and `engine_version` not null). A
fill deletes the project's engine placements and then all its threads, so a placement in a thread would
go by cascade. New chains are placed in the mailbox batch transaction; candidates are chains with no
placement row. The merge hook `carry_placement` keeps the earliest placement. The chain page
`/chains/:id` belongs to `correspondence` and knows nothing of projects (`correspondence` never imports
`projects`).

User decisions of this change: the path «new capability»; rules go to task 1.5; a chain is moved on its
own page; targets are a thread, «Неразобранное» or a new named thread; «Убрать из проекта» keeps the
chain out for good; «Заполнить» on a filled project is the re-sorting and keeps placements by hand with
their threads. Following the PRD priority, a placement by hand wins over the engine's on a merge.

## Goals / Non-Goals

**Goals:**
- One placement row per chain stays the single source of «where is this chain»; «taken out by hand» is
  such a row too, so every existing «chains with no placement» query keeps excluding it without change.
- The engine's code paths change only in what they delete: a fill drops engine rows and threads with no
  placement by hand; nothing else learns about kinds.
- Every hand action runs under the same lock of the user's project rows as a fill and the reading loop.

**Non-Goals:**
- Rules (task 1.5), though `kind` will take `rule` there without a new design.
- Renaming, merging, deleting threads; moving from the tree; batch moves.

## Decisions

### «Taken out by hand» is a placement row

`chain_placements.kind` takes `engine`, `manual` and `excluded`. An `excluded` row has no project and
no thread. Because candidates of a fill and of `place_new_chains` are «chains without a row», an
excluded chain is never scored, with no change to those queries.

Alternative: a separate table of excluded chains. Rejected: every candidate query and the merge hook
would need a second lookup, and «one row per chain» would no longer answer «where is it».

### Moving a chain

`PUT /placements/{chain_id}` in one transaction, under `lock_projects_for_owner`:
1. The chain must be the user's (`correspondence` service lookup), the project the user's, the thread
   (if given) a thread of that project — else 404 `not_found`.
2. A new thread name creates a thread at the next `position` of the project.
3. The chain's row is replaced by a `manual` row (`similarity` and `engine_version` null,
   `placed_at` now) — also when the target is the place it already has (pinning).
4. The thread the chain left is deleted if no placement points to it any more.

The project's `filled_at` is not touched: placing by hand into a project never filled does not make the
engine place new chains there.

### Taking a chain out

`DELETE /placements/{chain_id}` replaces the row with an `excluded` one and deletes the left thread if
empty. On a chain already out or in no project it answers 409 `chain_not_in_project`; the SPA shows the
button only for a chain in a project.

### Re-sorting («Заполнить» on a filled project)

The fill's first step becomes: delete the project's `engine` rows, then the threads that no `manual`
row points to. The remaining threads keep their ids, names and positions, and the `Placer` starts from
them with the documents of their manual chains, exactly as `place_new_chains` starts from existing
threads; new threads get positions after the highest kept one. Manual chains are not candidates (they
have a row), so they are never re-scored.

Alternative: rebuild all threads and keep only the manual chains' thread names. Rejected: thread
identity would change under the user, and two kept threads with one name would collapse.

### Merging chains

`carry_placement_for_owner` orders the candidate rows by a kind rank first — `manual` and `excluded`
(both by hand) before `engine` — then by the existing order (`placed_at`, project, thread). A survivor
`excluded` row stays excluded.

### Data model (revision `0006`)

`chain_placements`:
- `project_id` and `similarity`, `engine_version` become nullable;
- the check `kind` becomes `kind in ('engine', 'manual', 'excluded')`;
- a new check `shape`: `engine` has project, similarity and version; `manual` has project and no
  similarity or version; `excluded` has no project, thread, similarity or version.

Existing rows are all `engine` with every column set, so they pass the new checks untouched. Downgrade
to `0005` deletes `manual` and `excluded` rows first (the chains become «in no project»), then restores
the old checks and not-null columns; projects, threads and engine placements survive.

### Who may do what

Every route needs a signed-in user and, when it changes state, a matching `Origin` (FR-17, FR-20). Each
query carries the owner filter: the chain, the project and the thread are looked up for the caller
only, so another user's id is indistinguishable from an unknown one (404). No email text leaves the
installation.

## Interface

Paths are under `/api/v1`; every route needs a signed-in user (else 401 `not_signed_in`);
state-changing routes need a matching `Origin` (else 403 `forbidden_origin`). Another user's id answers
404 `not_found`.

### Schemas

- `Placement` (changed): `{kind: "engine" | "manual", engine_version: str | null, similarity: float | null}`
  — both null exactly when `kind` is `"manual"`.
- `ThreadSummary`: `{id: uuid, name: str}`
- `ChainLocation`: `{state: "placed" | "none" | "excluded", project: {id: uuid, name: str} | null, thread: ThreadSummary | null, placement: Placement | null}`
  — `project` and `placement` set exactly when `state` is `"placed"`; `thread` null is «Неразобранное».
- `PlacementMove` (request): `{project_id: uuid, thread_id: uuid | null, new_thread_name: str | null}` —
  at most one of `thread_id` and `new_thread_name`; both null is «Неразобранное»; the name stripped,
  1–100 characters.

### Routes

| Route | Body | Success | Errors |
|---|---|---|---|
| `GET /placements/{chain_id}` | — | 200 `ChainLocation` | 404 `not_found` |
| `PUT /placements/{chain_id}` | `PlacementMove` | 200 `ChainLocation` | 404 `not_found`, 422 `validation_failed` |
| `DELETE /placements/{chain_id}` | — | 200 `ChainLocation` | 404 `not_found`, 409 `chain_not_in_project` |
| `GET /projects/{id}/threads` | — | 200 `ThreadSummary[]` in thread order | 404 `not_found` |

`POST /projects/{id}/fill` keeps its contract; its behavior follows FR-36 as modified.

### Error messages (Russian, exact)

| Code | Message |
|---|---|
| `chain_not_in_project` | «Цепочка не входит ни в один проект» |
| field messages | «Укажите название ветки», «Название ветки — не длиннее 100 символов», «Выберите либо ветку, либо новую ветку» |

### SPA

- Chain page (`/chains/:id`): a block «Проект» above the emails showing
  «<project> → <thread> · <explanation>», «<project> → Неразобранное · <explanation>», «Вне проектов» or
  «Вне проектов · убрана вручную»; the explanation is «Вручную» or «Движок <version> · сходство <N>%».
  The form «Перенести»: select «Проект» (the user's projects), select «Ветка» («Неразобранное», the
  project's threads, «Новая ветка…»), the field «Название ветки» for a new thread, button «Перенести».
  Button «Убрать из проекта» only for a placed chain. A project name links to `/projects/:id`.
- Project page: «Вручную» instead of the engine explanation for chains placed by hand; the confirmation
  of «Заполнить» on a project with chains reads «Пересобрать проект? Движок разложит его переписку
  заново, а цепочки, размещённые вручную, останутся на месте» with «Пересобрать» and «Отмена».

### Test seams

- As in task 1.3: `get_placement_engine` → `FakePlacementEngine`; `read_due_mailboxes(..., engine=...)`
  with `FakeMailReader`; raw emails from `backend/tests/mail_factory.py`; the project factory in
  `backend/tests/factories.py`. New factory helpers: move a chain by hand and take it out through the API.

## Risks / Trade-offs

- [Nullable `project_id` weakens the schema] → the `shape` check keeps every kind's columns exact.
- [A user pins many chains, then the engine has little to do on re-sorting] → intended: hand wins.
- [A hand placement into a never-filled project] → the project stays unfilled, so the engine places no
  new chains there until «Заполнить»; the page still shows its chains.
- [Moving and the reading loop race on one chain] → both take the lock of the user's project rows.

## Migration Plan

Revision `0006` alters `chain_placements` only (nullable columns, new checks); existing rows pass as
they are. Downgrade to `0005` deletes `manual` and `excluded` rows, then restores the checks and
not-null columns. No new dependency, no new env var.
