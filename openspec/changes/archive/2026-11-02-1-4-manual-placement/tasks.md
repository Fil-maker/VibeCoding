# Tasks

One code cycle (`.claude/skills/feature/code-step.md`) per slice, each with its own sandbox, red check
and `close`: groups 1–2 (schema and backend, FR-35…FR-42), group 3 (SPA). `test-writer` writes the
slice's tests from the brief; `code-writer` writes the slice's groups. Tests sit only at the seams of
design «Test seams»: the HTTP API, `read_due_mailboxes`, the migration chain, the SPA components.
Implementation docs are updated at `/finish` through `/document`; product docs in group 4.

## 1. Schema

- [x] 1.1 `PlacementKind` gains `manual` and `excluded`; revision `0006` per design «Data model» (nullable columns, checks `kind` and `shape`, downgrade deleting `manual` and `excluded` rows) — check - `alembic upgrade head`, `alembic downgrade 0005`, `alembic upgrade head` and `alembic check` succeed against the test database
- [x] 1.2 Factory helpers in `backend/tests/factories.py` that move a chain by hand and take it out through the API — check - used by the scenario tests of group 2

## 2. Placement by hand (FR-35…FR-42)

- [x] 2.1 Routes `GET`/`PUT`/`DELETE /placements/{chain_id}` and `GET /projects/{id}/threads` per design «Moving a chain», «Taking a chain out» and «Interface», under the lock of the user's projects, the owner filter on chain, project and thread, the empty left thread deleted — check - the FR-40 and FR-41 scenario tests pass
- [x] 2.2 Re-sorting per design «Re-sorting»: the fill drops engine rows and threads with no manual row and places from the kept threads; `carry_placement_for_owner` ranks placements by hand first per design «Merging chains»; `Placement` schema with nullable `engine_version` and `similarity` — check - the FR-35, FR-36, FR-37, FR-39 and FR-42 scenario tests and the task 1.3 suites pass
- [x] 2.3 Scenario tests for FR-40…FR-42 and the new or changed scenarios of FR-35, FR-36, FR-37, FR-39 (`test-writer`, sandbox): moving to another project's thread, placing a chain of no project, a new thread, pinning, an empty thread disappears, empty and 101-character thread names, both `thread_id` and `new_thread_name`, a thread of another project, Вера with Анна's project, thread and chain ids; taking out, a repeated take-out (409), the engine not taking it back by fill or by a new email, placing it back; a reply in a chain placed by hand, joined with an engine chain, joined with a chain taken out; filling again keeps manual chains and their thread names and adds engine chains to a kept thread; the placement explanation `manual` without similarity; a fill skipping a chain taken out — check - red before the code, green after `tdd_sandbox.py close`

## 3. SPA

- [x] 3.1 `just api-client`; the block «Проект» on the chain page with the form «Перенести» and «Убрать из проекта»; «Вручную» in the project tree; the new confirmation text — all per design «SPA» with the exact Russian texts — check - `pnpm --dir frontend lint`, `typecheck`, `build` pass and the client freshness check in `just check` passes
- [x] 3.2 Component tests (`test-writer`, sandbox): the four location texts of the chain page, moving into a thread, into «Неразобранное» and into a new thread, the thread-name errors, «Убрать из проекта» shown only for a placed chain, «Вручную» in the tree, the new confirmation and its cancel — check - red before the code, green after `close`

## 4. Product docs

- [x] 4.1 `docs/domain.md`: glossary — Placement gains «by hand» and «taken out by hand»; requirements map and «Last FR number: FR-42» at archive — check - `just check` doc facts pass
- [x] 4.2 `docs/ideas.md`: «Rules and manual placement» leaves (tasks 1.4 and 1.5); add «Edit threads by hand» (rename, merge, delete threads, move from the tree, move several chains) — check - the entries exist and nothing stale is linked

## 5. Verification

- [x] 5.1 `just check` passes — check - all PASS
- [x] 5.2 `/test` with `all` passes — check - backend unit, backend database and frontend suites report counts, none NOT PRESENT
- [x] 5.3 Manual flow 1 (`flow-checker`, preview + GreenMail after `just demo-mail`): sign up a throwaway `flow-1-4-manual@example.test`, connect both demo mailboxes, wait for «Прочитан …»; create and fill «Ремонт офиса» and «Закупка техники»; open «Акт скрытых работ», move it into a new thread «Акты» of «Ремонт офиса» → the page shows «Ремонт офиса → Акты · Вручную», the tree shows «Акты» with «Вручную» — check - its PASS report
- [x] 5.4 Manual flow 2: press «Заполнить» on «Ремонт офиса», read the new confirmation, confirm → «Акт скрытых работ» still in «Акты» with «Вручную»; open a chain of «Закупка техники», press «Убрать из проекта» → «Вне проектов · убрана вручную»; fill «Закупка техники» again → that chain stays out — check - its PASS report
- [x] 5.5 Manual flow 3: `just demo-mail add-new`, press «Обновить» on the mailbox → chains placed by hand and taken out have not moved — check - its PASS report; test data cleaned up

## 6. Done when

- [x] 6.1 On the page of a chain the user moves it into a thread of any of their projects, into «Неразобранное» or into a new thread they name, and the chain then shows «Вручную» — check - 5.3 and the FR-40 tests
- [x] 6.2 A chain moved by hand stays where the user put it: a new email in it, a mailbox read and «Заполнить» never move it — check - 5.4, 5.5 and the FR-42, FR-36 tests
- [x] 6.3 «Убрать из проекта» takes a chain out of its project, and the engine never places it again by itself — check - 5.4 and the FR-41, FR-35, FR-39 tests
- [x] 6.4 «Заполнить» on a filled project keeps the chains placed by hand and the threads holding them, and lays out the rest again — check - 5.4 and the FR-36 tests
- [x] 6.5 Every chain in a project tree shows whether it was placed by hand or by the engine — check - 5.3 and the FR-37 tests
- [x] 6.6 `just check` and `just test-all` pass — check - 5.1 and 5.2

## Workflow follow-up

- `/finish 1.4`: invariant review, `openspec archive 1-4-manual-placement --yes`, `/document` (architecture «Data model», «Routes and API»; the engine guide article on re-sorting), `/journal`, `/commit` with `feat:`.
