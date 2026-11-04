# Proposal

## Why

Task 1.10 «Edit and delete a project» of `docs/plan.md`. A user's projects change while the work goes on
(`docs/prd.md`: the user describes their projects, and the tree follows them), but task 1.3 can only
create a project: a typo in a name, a description that has drifted from the real work, or a project
created by mistake stays for ever and clutters «Проекты», the rules and the chain pages.

## What Changes

- On the page of a project, «Изменить» changes its name and description by the checks of creation
  (FR-32). Changing the description moves no chain; a filled project whose description changed after its
  last filling shows a hint to fill it again, until it is filled.
- On the page of a project, «Удалить проект» deletes it after a confirmation that names how many chains
  leave the project and how many rules go with it. The project, its threads and the rules targeting it
  are deleted; every chain that was in it becomes taken out by hand (FR-41), so neither the engine nor a
  rule places it again by itself; the emails and chains stay in «Переписка».
- The invariant «History is kept» is worded more exactly in `docs/prd.md` and `CLAUDE.md`: the history of
  a project is kept while the project exists; only the user deletes a project, after a confirmation, and
  its emails and chains stay.

Out of scope (remain in `docs/ideas.md`): renaming, merging and deleting threads («Threads by hand»);
undoing a deletion or a recycle bin; deleting emails or chains («Deleting a disconnected mailbox's
emails»). The entry «Edit and delete a project» leaves `docs/ideas.md`: this change does it.

Touched invariants: «History is kept» — deleting a project is an explicit act of the user, the chains
become taken out by hand rather than free for the engine, and the wording is refined by the user's
decision. «Reproducible placement» — a changed description makes the engine's earlier similarities
stale; the hint makes it visible and nothing moves until the user fills again. «Access boundary» — both
actions answer «not found» for another user's project. «Mailbox read-only» is not touched: no email is
deleted or changed.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `projects`: ADDED FR-55 «Edit a project» and FR-56 «Delete a project».
- `chain-placement`: FR-41 «Take a chain out of projects» also covers the chains of a deleted project.
- `placement-rules`: FR-45 «Edit and delete a rule» — a rule is also deleted with its target project.

## Impact

- Backend `projects` module: `PATCH /api/v1/projects/{id}` and `DELETE /api/v1/projects/{id}`, a read of
  what a deletion touches, a column for when the description last changed (one Alembic migration).
- SPA `features/projects/ProjectPage.tsx`: the edit form, the hint, the delete button with its
  confirmation; the regenerated API client.
- Docs: `docs/prd.md` and `CLAUDE.md` invariant wording, `docs/domain.md` glossary «Project» and the
  requirements map, `docs/ideas.md`.
