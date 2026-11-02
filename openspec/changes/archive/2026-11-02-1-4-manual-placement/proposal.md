# Proposal

## Why

The engine makes mistakes, and after task 1.3 the user cannot fix them: a misplaced chain stays where
the engine put it, a chain the engine missed cannot be added, and «Заполнить» on a filled project throws
away every thread. The user must be able to fix the tree for good (`docs/prd.md` «Business functions»:
«Rules and placement by hand; re-sort a project by an explicit action»; invariant «History is kept»).
This is task 1.4 of `docs/plan.md`; the rules of the same idea are task 1.5.

## What Changes

- The page of a reply chain shows where the chain is — project and thread, «Неразобранное», or out of
  projects — and lets the user move it by hand into any of their projects: into a thread, into
  «Неразобранное» or into a new thread they name. Moving a chain to the place where it already is pins
  it there.
- «Убрать из проекта» takes a chain out of its project for good: the engine never places it again by
  itself; only the user can place it back by hand.
- A placement by hand is never changed by the engine: not by a new email in the chain, not by a mailbox
  read, not by «Заполнить». When chains are joined, a placement by hand wins over the engine's.
- «Заполнить» on a filled project becomes the explicit re-sorting: the chains placed by hand and the
  threads holding them stay with their names; the engine lays out the rest again, into those threads or
  new ones. The confirmation says so.
- Every chain in a tree shows «Вручную» or, as before, «Движок <version> · сходство <N>%».
- A thread left without chains disappears.

Out of scope:
- Rules by address, domain or subject (task 1.5 «Rules»).
- Renaming, merging and deleting threads by hand; moving a chain from the project tree; moving several
  chains at once — deferred to `docs/ideas.md` «Edit threads by hand».
- Showing a chain's project in «Переписка» (already in `docs/ideas.md`).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `chain-placement`: new requirements FR-40 «Place a chain by hand», FR-41 «Take a chain out of
  projects», FR-42 «Placements by hand are kept»; FR-35 and FR-39 no longer take a chain taken out by
  hand; FR-36 keeps the placements by hand and their threads; FR-37 explains a placement by hand.

## Impact

- Product invariants: **Explainable placement** (a placement now says «by hand» or «by the engine»),
  **History is kept** (only the user moves a chain; a re-sorting keeps the placements by hand),
  **Access boundary** (a user moves only their own chains into their own projects and threads). No
  invariant changes its meaning; all follow `docs/prd.md` as written.
- Backend: `projects` module — placement routes for one chain, the threads of a project, a re-sorting
  fill, the merge hook preferring placements by hand; migration `0006` widens `chain_placements`.
- SPA: a block «Проект» on the chain page with the form «Перенести» and «Убрать из проекта»; «Вручную»
  in the tree; the new confirmation text; the regenerated API client.
- Docs: `docs/domain.md` (requirements map, glossary: Placement by hand), `docs/architecture.md`,
  the engine guide article, `docs/ideas.md`.
