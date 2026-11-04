# Design

## Context

A project (`projects` table) has a name, a description and `filled_at`. Its threads and the placements of
its chains reference it with `ON DELETE CASCADE`, and so do the rules of the `rules` module
(`rules.project_id`). A placement row of kind `excluded` (FR-41) has no project and no thread; the engine
(FR-35, FR-39) and the rules (FR-46, FR-47) already skip it. `service.py` (355 lines) and
`repository.py` (393 lines) of the projects module are near the 300-line aim, so the new actions get
their own files. The project page is `frontend/src/features/projects/ProjectPage.tsx`; buttons of the
danger kind and the confirmation pattern exist since task 1.8.

## Goals / Non-Goals

**Goals:**
- Edit the name and description of a project (FR-55) with the checks and messages of FR-32.
- Show that a filled project's description changed after its last filling (FR-55).
- Delete a project after a confirmation with live counts (FR-56); its chains become `excluded` (FR-41),
  its threads and rules go (FR-45).

**Non-Goals:**
- Undo, a recycle bin, or an audit trail of deleted projects.
- Re-sorting on a description change: the user presses «Заполнить» (FR-36).
- Thread editing, deleting emails or chains.

## Decisions

### D1. The chains of a deleted project become `excluded`

Decided by the user. In one transaction, every placement row of the project is rewritten to kind
`excluded` (project, thread, similarity, engine version and rule columns cleared, `placed_at` set to now),
then the project row is deleted. Rewriting first matters: the cascade would otherwise delete the
placement rows and the chains would become free (in no project, not taken out).
Alternatives: free chains (the engine and rules could take them into another project); `excluded` only
for chains placed by hand. Rejected by the user: a deleted project's correspondence must not drift into
other projects by itself.

### D2. Threads and rules go by the existing cascade

The project row's deletion cascades to `threads` and `rules`; the projects module does not call the rules
module to delete. The confirmation reads the rule count through a new read of `rules/service.py`,
`count_rules_targeting(user, project_id)`, since another module is used only through its service
(`server-architecture.md`); the projects module already imports `rules.service`.
Alternative: refuse the deletion while rules target the project. Rejected by the user.

### D3. A column for when the description last changed

`projects.description_changed_at` (timestamp with time zone, nullable). Set to now by an edit whose
trimmed description differs from the stored one; untouched by a name-only edit. The page's hint shows
when `filled_at` is set and `description_changed_at > filled_at`. Filling sets `filled_at` to now, so the
hint goes by itself.
Alternatives: store the description used at the last filling and compare texts (doubles a 2000-character
field); a boolean flag reset by filling (two writers must keep it right). The timestamp is one write in
one place.

### D4. The confirmation reads fresh counts

The SPA asks the server for the counts when the user presses «Удалить проект», not from the tree it
already shows, so the numbers are right even after a mailbox read in another tab. The deletion itself
does not take the counts: it deletes what is there at that moment.

### D5. Edit and delete live in a new file of the service layer

`project_editing.py` (service functions) with its repository queries, so `service.py` and `repository.py`
stay under 500 lines. The router stays the single entry.

### Data and migration

Migration `0008_project_description_changed_at` adds the nullable column; existing projects get null and
show no hint. Downgrade drops the column. No data is rewritten. A deleted project cannot be restored by
a rollback — that is the feature.

### Who may call

Both actions need a signed-in user (FR-17) and the same-site check (FR-20, answer 403). The project is
looked up by id under the owner filter; another user's or a deleted project answers 404 and nothing is
written. Only the caller's own placement rows, threads and rules are touched.

## Interface

HTTP, under `/api/v1/projects`:

- `PATCH /{project_id}` — body `{ "name": string, "description": string }`, both required, the checks and
  422 messages of `POST /projects`. 200 with `ProjectTree`. 409 `Проект с таким названием уже есть` when
  another project of the user has the name ignoring letter case. 401, 403, 404.
- `GET /{project_id}/deletion` — 200 with `{ "chain_count": int, "rule_count": int }`: the chains in the
  project (threads and «Неразобранное») and the rules targeting it. 401, 404.
- `DELETE /{project_id}` — 204, no body. 401, 403, 404.
- `ProjectTree` gains `description_changed: bool` — true exactly when the hint of FR-55 is shown.

SPA texts (exact): button «Изменить», form buttons «Сохранить» and «Отмена»; the hint «Описание изменено
после заполнения: нажмите «Заполнить», чтобы пересобрать проект»; danger button «Удалить проект»; the
confirmation «Удалить проект «<name>»? Цепочек в проекте: N — они останутся в «Переписке» как убранные
вручную. Правил, ведущих в проект: M — они будут удалены. Письма не удаляются.» with «Удалить» and
«Отмена»; after the deletion the route is «Проекты» (`/projects`).

## Risks / Trade-offs

- Deletion cannot be undone. Mitigation: the confirmation with counts; the emails and chains stay, and
  the user can place the chains back by hand.
- A chain of a deleted project stays `excluded` for good, even for a later project about the same work;
  the user moves it by hand. Accepted by the user's decision D1.
- Cascade on `rules` crosses a module boundary at the database level only; it already exists since task
  1.5.
