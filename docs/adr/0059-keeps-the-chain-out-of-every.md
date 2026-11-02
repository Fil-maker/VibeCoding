# «Убрать из проекта» keeps the chain out of every project for good: the engine never places it again by itself; only the user can place it back by hand

Id: 0059 · Date: 02.11.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: 1.4.
- Migration 0006_manual_placements: chain_placements.project_id, similarity and engine_version become nullable; check kind in ('engine','manual','excluded'); new check ck_chain_placements_shape: engine rows have project, similarity and engine_version; manual rows have a project and no similarity/engine_version; excluded rows have no project, no thread, no similarity, no engine_version. Downgrade deletes manual and excluded rows.
- PlacementKind gains MANUAL ('manual', placed by hand) and EXCLUDED ('excluded', taken out of projects by hand: a row with null project_id); task 1.5 adds «by a rule».
- New routes: GET /api/v1/projects/{project_id}/threads (threads of a project in order, 401/404); router placements_router at /api/v1/placements: GET /{chain_id} returns ChainLocation (401/404); PUT /{chain_id} with PlacementMove moves the chain by hand into a thread, a new thread (new_thread_name) or «Неразобранное» of a project (401/403/404/422); DELETE /{chain_id} takes the chain out for good (401/403/404/409 chain_not_in_project «Цепочка не входит ни в один проект»).
- ChainLocation has state none | placed | excluded, project (id, name), thread (id, name) or null for «Неразобранное», placement (kind manual | engine, engine_version, similarity) — null for none and excluded.
- backend/app/modules/projects/hand_placing.py holds placing by hand: reading a chain's location, moving it, taking it out; a thread left without chains is deleted; a missing project or thread answers NotFound.
- Refilling a filled project («Заполнить») deletes only engine placements and threads holding no manual chain (repository delete_engine_placements_and_unpinned_threads_for_owner); manual chains and their threads stay, and the engine may add sure chains to a kept thread.
- Chains with any placement row — placed in a project or excluded — are never candidates for filling or for placing new chains (list_placed_chain_ids_for_owner).
- On a merge of chains (carry_placement_for_owner) a placement by hand wins over the engine's whatever the dates; among placements of one kind the earliest wins; excluded counts as by hand.
- correspondence.service.has_chain(session, user_id, chain_id) tells whether the chain is the user's, inside the caller's transaction; the projects module uses it to check a chain before placing it.
- SPA: frontend/src/features/projects/ChainPlacement.tsx shows on the chain page (/chains/:id, ChainPage.tsx) the block «Проект» with where the chain is («<project> → <thread or Неразобранное> · <Вручную | Движок v · сходство N%>», «Вне проектов», «Вне проектов · убрана вручную»), the button «Убрать из проекта» for a placed chain, and the form «Перенести» with selects «Проект», «Ветка» (threads, «Неразобранное», «Новая ветка…») and the field «Название ветки». «Ветка» starts at the chain's current thread while its own project is selected and resets to «Неразобранное» when another project is picked.
- frontend/src/features/projects/format.ts placementLabel renders «Вручную» for a manual placement and «Движок <version> · сходство <N>%» for an engine one; ProjectPage tree shows it for every chain and in «Неразобранное».
- SPA test helpers: frontend/src/test/chainPlacement.tsx (fixtures and API stubs for the chain page placement block); frontend/src/test/projectTrees.tsx gains placements by hand.
- Backend test helpers: backend/tests/hand_placement.py (seeding placements by hand); factories gain manual and excluded placements.

## Decision
«Убрать из проекта» keeps the chain out of every project for good: the engine never places it again by itself; only the user can place it back by hand

## Alternatives
plain removal the engine may undo; no removal in 1.4

## Reason
Навсегда вне проектов (рекомендую)
