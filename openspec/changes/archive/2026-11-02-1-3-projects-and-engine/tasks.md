# Tasks

One code cycle (`.claude/skills/feature/code-step.md`) per slice, each with its own sandbox, red check
and `close`: groups 1–2 (engine and schema), group 3 (FR-32…FR-34), group 4 (FR-35…FR-39), group 5
(SPA). `test-writer` writes the slice's tests from the brief; `code-writer` writes the slice's groups.
Tests sit only at the seams of design «Test seams»: the HTTP API, `read_due_mailboxes`, the public
`platform` functions, the migration chain, the SPA components. Implementation docs are updated at
`/finish` through `/document`; product docs in group 6.

## 1. Engine

- [x] 1.1 Add `snowballstemmer` to `backend/pyproject.toml` with an exact pin and to `uv.lock` — check - `uv sync --directory backend` succeeds
- [x] 1.2 `platform/placement_engine.py`: `PlacementEngine`, `LocalTextEngine` (`text-1`), `FakePlacementEngine`, `get_placement_engine` per design «Platform interface» and «Similarity» — check - unit tests: the same inputs in another order give the same scores; «смета» and «сметы» share a stem; quoted `>` lines do not count; scores have 4 decimals; the fake gives its key's value and 0.0 otherwise
- [x] 1.3 Tune the three thresholds of `text-1` on the ten demo chains and the three demo project descriptions, then freeze them as constants — check - a unit test over the demo `.eml` files puts each chain into its project and none into another

## 2. Schema

- [x] 2.1 Models of design «Data model» in `projects` and the revision `0005` — check - `alembic upgrade head`, `alembic downgrade 0004`, `alembic upgrade head` and `alembic check` succeed against the test database
- [x] 2.2 A factory in `backend/tests/factories.py` that creates a project through the API — check - used by the scenario tests of groups 3 and 4

## 3. Projects (FR-32…FR-34)

- [x] 3.1 `projects` module: create with the stripped, case-insensitive unique name, list with counts, the tree of design «The tree» through the `correspondence` service — routes, errors and texts of design «Interface» — check - the FR-32…FR-34 scenario tests pass
- [x] 3.2 Scenario tests for FR-32…FR-34 (`test-writer`, sandbox): create, empty and too long fields, the same name in another case, the same name for Вера, the list order and counts, empty list, only one's own projects, the tree with a chain under two counterparties and «Без контрагента», Вера against Анна's project id — check - red before the code, green after `tdd_sandbox.py close`

## 4. Placement (FR-35…FR-39)

- [x] 4.1 Fill per design «Filling a project» with the lock of the user's projects; `store_raw_messages` returns the chain ids that got an email and takes the merge hook; `place_new_chains` and `carry_placement` per design «Placing new chains» and «Merged chains keep the first placement»; `read_due_mailboxes` wires both with its `engine` argument — check - the FR-35…FR-39 scenario tests and the task 1.2 suites pass
- [x] 4.2 Scenario tests for FR-35…FR-39 (`test-writer`, sandbox): filling with the local engine on demo-like emails, threads and their names, «Неразобранное», chains of another project not taken, nothing matches, Вера's fill never takes Анна's chains, Вера against Анна's project id; filling again rebuilds; the shown similarity and version with the fake engine; twice the same tree; two users with another reading order get the same tree; another version shown only after filling again; a reply keeps its chain's place; a new chain into a thread, «Неразобранное» or nowhere; two placed chains joined keep the first placement; unfilled projects skipped; Вера's new chain never in Анна's project — check - red before the code, green after `close`

## 5. SPA

- [x] 5.1 `just api-client`; routes `/projects`, `/projects/new`, `/projects/:id` behind `RequireUser`; the pages of design «SPA pages» with the exact Russian texts; the link from the start page — check - `pnpm --dir frontend lint`, `typecheck`, `build` pass and the client freshness check in `just check` passes
- [x] 5.2 Component tests (`test-writer`, sandbox): the list with plural counts and the empty text, the create form and its errors, the tree with counterparties, threads and the placement line «Движок text-1 · сходство 43%», «Неразобранное», the two empty texts, the confirmation before filling again and its cancel, an unknown project → «Страница не найдена» — check - red before the code, green after `close`

## 6. Product docs

- [x] 6.1 `docs/domain.md`: glossary — Counterparty is one participant address for now, Thread named by its earliest chain, new terms Placement and Engine version; «Data and privacy» — no email text leaves the installation, projects and placements belong to one user; requirements map and «Last FR number: FR-39» at archive — check - `just check` doc facts pass
- [x] 6.2 `docs/ideas.md`: «Projects and placement» becomes task 1.3 and leaves; «Analysis engine» keeps only the open third-party model; add «Edit and delete a project» and «A chain's project in «Переписка»» — check - the entries exist and nothing stale is linked

## 7. Verification

- [x] 7.1 `just check` passes — check - all PASS
- [x] 7.2 `/test` with `all` passes — check - backend unit, backend database and frontend suites report counts, none NOT PRESENT
- [x] 7.3 Manual flow 1 (`flow-checker`, preview + GreenMail after `just demo-mail`): sign up a throwaway `flow-1-3-projects@example.test`, connect both demo mailboxes, wait for «Прочитан …»; create «Ремонт офиса» with the demo description, press «Заполнить» → the tree with Сергей Петров and Ольга Смирнова, each chain with «Движок text-1 · сходство N%» — check - its PASS report
- [x] 7.4 Manual flow 2: create and fill «Закупка техники» and «Конференция ТехФорум» → every demo chain in exactly one project; press «Заполнить» on «Ремонт офиса», cancel → no change, confirm → the same tree — check - its PASS report
- [x] 7.5 Manual flow 3: `just demo-mail add-new`, press «Обновить» on the mailbox → the reply sits in its chain's place; the other chains have not moved — check - its PASS report; test data cleaned up

## 8. Done when

- [x] 8.1 The user creates a project, presses «Заполнить» and sees the tree — check - 7.3 and the FR-32, FR-34, FR-35 tests
- [x] 8.2 Every placed chain shows why it is there, its similarity and the engine version — check - 7.3 and the FR-37 tests
- [x] 8.3 Chains the engine is not sure of go to «Неразобранное» — check - the FR-35 and FR-39 tests
- [x] 8.4 New emails take their place in the tree without moving chains already placed — check - 7.5 and the FR-39 tests
- [x] 8.5 Filling the same project from the same emails again gives the same tree — check - 7.4 and the FR-36, FR-38 tests
- [x] 8.6 `just check` and `just test-all` pass — check - 7.1 and 7.2

## Workflow follow-up

- `/finish 1.3`: invariant review, `openspec archive 1-3-projects-and-engine --yes`, `/document` (architecture «Components and processes», «Repository structure», «Layers», «Data model», «Routes and API»; tech «Stack»; a guide article on the engine), `/journal`, `/commit` with `feat:`.
