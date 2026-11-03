# Tasks

One code cycle (`.claude/skills/feature/code-step.md`) per slice, each with its own sandbox, red check
and `close`: group 1 (backend, FR-45…FR-47), group 2 (SPA). `test-writer` writes the slice's tests from
the brief; `code-writer` writes the slice's code. Tests sit only at the seams of design «Test seams»:
the HTTP API and the SPA components. Implementation docs are updated at `/finish` through `/document`;
product docs in group 3.

## 1. Moves of a rule (FR-45…FR-47)

- [x] 1.1 `rules.service.get_match_rule`; `projects/rule_applying.py` with the moves per design «Which chains a rule moves», «List, then apply what the user saw» and «One move», reusing the rule placement of `rule_placing.py` and `delete_thread_if_empty_for_owner`; `ProjectsService.list_rule_moves` and `apply_rule`; routes `GET`/`POST /placements/by-rule/{rule_id}` and the schemas of «Interface» — check - the FR-47 scenario tests pass, and the task 1.3–1.5 suites stay green
- [x] 1.2 Scenario tests (`test-writer`, sandbox), through the HTTP API: FR-47 — a chain in no project listed and moved into «Неразобранное» with the rule explanation; a chain of the engine moved into a new thread and gone from its old project; nothing moved without `POST`; a chain placed by hand and a chain taken out never listed nor moved even when their ids are sent; a stronger rule's chain not listed; an edited target moving the rule's earlier chains; an edited value leaving a no-longer-matching chain with its old explanation; a chain already in place not listed and keeping «Движок»; an empty list; a thread left empty deleted; a chain moved by hand between `GET` and `POST` skipped; a second identical `POST` moving 0; Вера with Анна's rule id on `GET` and `POST` → 404, Вера's own rule with Анна's chain ids → Анна's chains unmoved; more than 5000 ids → 422. FR-45 — an edit and a delete alone move nothing. FR-46 — «A new rule moves nothing» without apply — check - red before the code, green after `tdd_sandbox.py close`

## 2. SPA

- [x] 2.1 `just api-client`; on «Правила» the panel of design «SPA (page «Правила»)» after create and after edit, with the exact Russian texts, «Применить», «Не сейчас», «Подходящих цепочек нет», «Перемещено цепочек: <N>», disabled buttons during a request — check - `pnpm --dir frontend lint`, `typecheck`, `build` pass and the client freshness check in `just check` passes
- [x] 2.2 Component tests (`test-writer`, sandbox): the panel after create and after edit with each «откуда» form (out of projects, «Неразобранное», a thread) and each «куда» form; «Применить» sends exactly the listed ids and shows the count; «Не сейчас» sends nothing; the empty list text; buttons disabled while waiting — check - red before the code, green after `close`

## 3. Product docs

- [x] 3.1 `docs/domain.md`: glossary Rule — editing moves nothing until the user applies the rule or fills the project; requirements map row `placement-rules` gains FR-47; «Last FR number: FR-47» at archive — check - `just check` doc facts pass
- [x] 3.2 `docs/ideas.md`: remove «Apply a rule now»; add «Apply a rule later» (from a rule's row, several rules at once) — check - the entries are as stated and nothing links to the removed heading

## 4. Verification

- [x] 4.1 `just check` passes — check - all PASS
- [x] 4.2 `/test` with `all` passes — check - backend unit, backend database and frontend suites report counts, none NOT PRESENT
- [x] 4.3 Manual flow 1 (`flow-checker`, preview + GreenMail after `just demo-mail`): sign up a throwaway `flow-1-6-apply@example.test`, connect both demo mailboxes, wait for «Прочитан …»; create and fill «Ремонт офиса»; create «Закупка техники»; on «Правила» create «Домен» «techsnab.example» → «Закупка техники», thread «Поставки» → the panel lists the chains of Игорь Волков with where they are; press «Не сейчас» → the tree of «Ремонт офиса» is unchanged — check - its PASS report
- [x] 4.4 Manual flow 2: move one chain of Игорь Волков by hand into «Ремонт офиса»; edit the rule to thread «Мониторы» → the panel omits the chain moved by hand; press «Применить» → «Перемещено цепочек: N»; «Закупка техники» shows «Мониторы» with those chains and «Правило · домен techsnab.example», the chain moved by hand stays with «Вручную», and an emptied thread of «Ремонт офиса» is gone; create a rule matching nothing → «Подходящих цепочек нет» — check - its PASS report; test data cleaned up

## 5. Done when

- [x] 5.1 After the user saves a rule on «Правила», the page lists the chains it would move, each with where it is now and where it goes, with «Применить» and «Не сейчас» — check - 4.3 and the FR-47 tests
- [x] 5.2 On «Применить» those chains are in the rule's project and thread and show «Правило» with the rule; on «Не сейчас» nothing moves — check - 4.3, 4.4 and the FR-47 tests
- [x] 5.3 A chain in no project, placed by the engine (also in «Неразобранное») or placed by another rule is moved; a chain placed by hand or taken out of projects never is — check - 4.4 and the FR-47 tests
- [x] 5.4 A chain that a stronger rule wins stays where it is — check - the FR-47 tests
- [x] 5.5 After an edit, the chains the rule placed before that still match go to its new target, and those that no longer match stay where they are — check - 4.4 and the FR-47 tests
- [x] 5.6 A thread left empty by the move disappears — check - 4.4 and the FR-47 tests
- [x] 5.7 A rule that would move nothing says «Подходящих цепочек нет» and moves nothing — check - 4.4 and the FR-47 tests
- [x] 5.8 `just check` and `just test-all` pass — check - 4.1 and 4.2
