# Tasks

One code cycle (`.claude/skills/feature/code-step.md`) per slice, each with its own sandbox, red check
and `close`: groups 1–3 (schema and backend, FR-35…FR-46), group 4 (SPA). `test-writer` writes the
slice's tests from the brief; `code-writer` writes the slice's groups. Tests sit only at the seams of
design «Test seams»: the HTTP API, `read_due_mailboxes`, the migration chain, the pure matching
function, the SPA components. Implementation docs are updated at `/finish` through `/document`; product
docs in group 5.

## 1. Schema

- [x] 1.1 `PlacementKind` gains `rule`; revision `0007` per design «Data model» (table `placement_rules` with its checks and indexes; `chain_placements.rule_condition`, `rule_value`; checks `kind` and `shape` widened; downgrade deleting `rule` rows) — check - `alembic upgrade head`, `alembic downgrade 0006`, `alembic upgrade head` and `alembic check` succeed against the test database
- [x] 1.2 Factory helper in `backend/tests/factories.py` that creates a rule through the API — check - used by the scenario tests of groups 2 and 3

## 2. Rules (FR-43…FR-45)

- [x] 2.1 Routes `GET`/`POST /rules`, `PUT`/`DELETE /rules/{rule_id}` per design «Rules live in the `projects` module», «Who may do what» and «Interface»: validation and normalisation of `RuleInput`, the owner filter on rule and target project, `rule_exists` (also on the unique index race), `too_many_rules` at 200, the list in priority order; no placement changes — check - the FR-43…FR-45 scenario tests pass
- [x] 2.2 Scenario tests for FR-43…FR-45 (`test-writer`, sandbox): address kept lower-cased with its target, empty and spaces-only thread name as «Неразобранное», each invalid value with its exact message, no project, a repeated rule in another letter case on create and on edit, the 201st rule, Вера with Анна's project, rule ids on `PUT` and `DELETE`, the priority order of the list, an empty list, Вера not seeing Анна's rules, edit and delete leaving placements unchanged — check - red before the code, green after `tdd_sandbox.py close`

## 3. Placement by rules (FR-35…FR-37, FR-39, FR-42, FR-46)

- [x] 3.1 `ChainDocument.senders` in `correspondence` per design «Senders of a chain»; the pure matching function per design «Matching and priority are pure»; placing by a rule into a thread by name per design «Thread by name» with the rule copied into the row — check - the FR-46 unit tests of the matching function pass
- [x] 3.2 `place_new_chains` places by rules before the engine per design «New chains»; the fill drops `engine` and `rule` rows and places by rules first per design «Fill and filling again»; `carry_placement_for_owner` ranks per design «Merging chains»; `Placement` schema with `rule` — check - the FR-35, FR-36, FR-37, FR-39, FR-42 and FR-46 scenario tests and the task 1.3–1.4 suites pass
- [x] 3.3 Scenario tests (`test-writer`, sandbox): FR-46 — by address into a new thread, by domain with a subdomain and not a look-alike domain, by subject words and not «Акт сверки», a word inside another word, letter case and «ё», an existing thread of that name, address over domain, the earlier of one kind, a chain placed by hand, a chain taken out, a new rule moving nothing, Вера's chain and Анна's rule; FR-39 — a rule before a sure engine match, a rule into an unfilled project; FR-35 — a rule of this project first, a rule of another project keeping a chain out; FR-36 — an edited rule on filling again, a deleted rule on filling again; FR-37 — the three rule explanations in the tree and in `ChainLocation`, unchanged after the rule's edit and deletion; FR-42 — a rule's placement over the engine's, by hand over a rule's; plus unit tests of the matching function — check - red before the code, green after `close`

## 4. SPA

- [x] 4.1 `just api-client`; the link «Правила» in the header; the page `/rules` with the form, the list, «Изменить» and «Удалить» with its confirmation, «Правил пока нет», «Сначала создайте проект»; the rule explanations in the project tree and on the chain page — all per design «SPA» with the exact Russian texts — check - `pnpm --dir frontend lint`, `typecheck`, `build` pass and the client freshness check in `just check` passes
- [x] 4.2 Component tests (`test-writer`, sandbox): creating a rule of each condition, the field errors and «Такое правило уже есть» from the server, the list text with a thread and with «Неразобранное», editing in place and its cancel, deleting with the confirmation and its cancel, the empty list, no projects, the three explanations in the tree and on the chain page — check - red before the code, green after `close`

## 5. Product docs

- [x] 5.1 `docs/domain.md`: glossary — new term Rule; Placement gains «by a rule»; requirements map row `placement-rules` FR-43…FR-45 and `chain-placement` gains FR-46; «Last FR number: FR-46» at archive — check - `just check` doc facts pass
- [x] 5.2 `docs/ideas.md`: add «Apply a rule now», «Richer rules» (recipient, body, «or»/«not», manual order) and «A rule from a chain» — check - the entries exist and nothing stale is linked

## 6. Verification

- [x] 6.1 `just check` passes — check - all PASS
- [x] 6.2 `/test` with `all` passes — check - backend unit, backend database and frontend suites report counts, none NOT PRESENT
- [x] 6.3 Manual flow 1 (`flow-checker`, preview + GreenMail after `just demo-mail`): sign up a throwaway `flow-1-5-rules@example.test`, connect both demo mailboxes, wait for «Прочитан …»; create «Ремонт офиса» and «Закупка техники»; on «Правила» create «Адрес отправителя» «i.volkov@techsnab.example» → «Закупка техники», thread «Поставки», and «Слова темы» «акт работ» → «Ремонт офиса», thread «Акты»; check the list order and texts; try a repeated rule → «Такое правило уже есть» — check - its PASS report
- [x] 6.4 Manual flow 2: fill «Ремонт офиса» and «Закупка техники» → «Акт скрытых работ» is in «Акты» with «Правило · слова темы «акт работ»», the chains of Игорь Волков are in «Поставки» with «Правило · адрес i.volkov@techsnab.example»; open one of them → the chain page shows the same explanation; move one by hand elsewhere, change its rule's thread to «Сервер», fill again → the chain moved by hand stays, the others are in «Сервер» — check - its PASS report
- [x] 6.5 Manual flow 3: `just demo-mail add-new`, press «Обновить» on the mailbox → a new chain matching a rule is in the rule's project and thread with «Правило»; delete a rule → its chains stay with the old explanation — check - its PASS report; test data cleaned up

## 7. Done when

- [x] 7.1 On the page «Правила» the user creates a rule by sender address, domain or subject words with a target project and thread name, and edits or deletes it — check - 6.3 and the FR-43…FR-45 tests
- [x] 7.2 A new chain matching a rule goes into its project and thread before the engine compares it, and the thread is created when the project has none of that name — check - 6.5 and the FR-39, FR-46 tests
- [x] 7.3 «Заполнить» places the chains matching the project's rules by those rules first and gives the rest to the engine — check - 6.4 and the FR-35, FR-36 tests
- [x] 7.4 When two rules match a chain, an address wins over a domain and a domain over subject words — check - the FR-46 tests and the matching unit tests
- [x] 7.5 A chain placed by a rule shows «Правило» and the rule — check - 6.4 and the FR-37 tests
- [x] 7.6 A rule never moves a chain placed by hand or taken out of projects — check - 6.4 and the FR-46, FR-42 tests
- [x] 7.7 `just check` and `just test-all` pass — check - 6.1 and 6.2

## Workflow follow-up

- `/finish 1.5`: invariant review, `openspec archive 1-5-rules --yes`, `/document` (architecture «Data model», «Routes and API»; the engine guide article on rules), `/journal`, `/commit` with `feat:`.
