# «Заполнить» on a filled project is an explicit user action with confirmation that rebuilds the engine's placements of the project from the same emails and gives the same tree; task 1.4 makes it keep manual placements

Id: 0054 · Date: 29.10.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: 1.3.
- New backend module projects (backend/app/modules/projects/): projects, threads, placements, the tree, fill and placing of new chains; routes GET/POST /api/v1/projects, GET /api/v1/projects/{id}, POST /api/v1/projects/{id}/fill; errors 409 project_exists, 404 not_found, 422 validation_failed
- projects reads chains, emails and participants only through the correspondence service: store_raw_messages(..., on_merge) returns the ids of chains that got a new email; list_chain_documents, list_chain_facts, get_latest_sender_names
- Engine backend/app/platform/placement_engine.py: PlacementEngine protocol, LocalTextEngine version text-1 (TF-IDF cosine over Snowball stems, Russian for Cyrillic and English for Latin words, stop words dropped, quoted > lines dropped, ё→е, scores rounded to 4 decimals, IDF over the user's whole chain corpus), FakePlacementEngine for tests, get_placement_engine dependency (lazy, app.state.placement_engine)
- text-1 thresholds are constants of the version: sure 0.15, lower 0.05, thread 0.15; tuned on the ten demo chains of docker/greenmail/demo and three demo descriptions; any change of a threshold, stop word or stemmer version is a new engine version
- Fill: one transaction under FOR UPDATE of all the user's project rows; drop the project's threads and engine placements; candidates are the user's chains with no placement; score >= sure → thread, lower <= score < sure → Неразобранное (thread_id null), below lower → out; threaded chains in reading order (first email sent_at, first subject, first email key, never chain id) join the most similar thread at or above thread threshold (ties to the earlier thread) or start a new thread named by their first subject; filled_at set
- New chains: read_due_mailboxes(database, reader, clock, settings, engine=None → LocalTextEngine) calls place_new_chains in each batch's transaction; unplaced chains that got an email are scored against every filled project, the best (ties: project created first, then name) gets the same bands and thread rule; placed chains are never re-scored; carry_placement keeps on a merged chain the placement with the earliest placed_at
- Tables of revision 0005: projects (user_id, name varchar 100 unique per user by lower(name), description, filled_at, created_at), threads (user_id, project_id, name, position unique per project, created_at), chain_placements (chain_id PK → reply_chains cascade, user_id, project_id, thread_id null = Неразобранное, kind check in ('engine'), similarity numeric(5,4), engine_version varchar 32, placed_at)
- Tree built per request: counterparties = participant addresses named by the latest display name sent from that address, else the address, sorted by name case-insensitively then address, «Без контрагента» (address null) last; threads by position; chains in a thread by reading order; Неразобранное by similarity descending then reading order
- New dependency snowballstemmer==3.0.1 (exact pin; its version is part of the engine version); no new env vars
- SPA: frontend/src/features/projects/ (ProjectsPage, NewProjectPage, ProjectPage, ProjectPage.module.css, format.ts with plural labels and «Движок <version> · сходство <N>%»); routes /projects, /projects/new, /projects/:id behind RequireUser; start page link «Проекты»; FormField got a multiline prop rendering a textarea; test helpers frontend/src/test/projectTrees.tsx and appHarness.tsx extended

## Decision
«Заполнить» on a filled project is an explicit user action with confirmation that rebuilds the engine's placements of the project from the same emails and gives the same tree; task 1.4 makes it keep manual placements

## Alternatives
only an empty project can be filled

## Reason
Пользователь выбрал «Пересобирает заново»
