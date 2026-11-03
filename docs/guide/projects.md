# Projects

Updated 03.11.2026

**Code:** `backend/app/modules/projects/` (`router.py`, `service.py`, `hand_placing.py`, `rule_placing.py`, `rule_applying.py`, `domain.py`,
`placing.py`, `repository.py`, `models.py`, `schemas.py`, `errors.py`), the platform file `backend/app/platform/placement_engine.py`, its unit tests
`backend/app/platform/test_placement_engine.py`, the wiring in `backend/app/modules/mailboxes/service.py`, the functions of
`backend/app/modules/correspondence/service.py` that projects use (among them `has_chain`) and its `MergeHook`, the migrations
`backend/migrations/versions/0005_projects_and_placements.py`, `0006_manual_placements.py` and `0007_placement_rules.py`, the integration
tests `backend/tests/integration/test_projects_*.py`, `test_placement_*.py` and the rule groups, the SPA's
`frontend/src/features/projects/ChainPlacement.tsx`, and the test seams `backend/tests/project_trees.py`, `backend/tests/hand_placement.py`,
`backend/tests/rule_support.py`, `Factories.create_project` and the placement helpers in `backend/tests/factories.py`. The rules module
`backend/app/modules/rules/` is in [Rules](rules.md).

**Requirements:** [FR-32 … FR-34](../../openspec/specs/projects/spec.md) projects (create, list, show as a tree),
[FR-35 … FR-42](../../openspec/specs/chain-placement/spec.md) chain placement (fill, fill again, every placement explained,
reproducible placement, placing new chains, placing a chain by hand, taking a chain out of projects, placements by hand kept),
[FR-43 … FR-45](../../openspec/specs/placement-rules/spec.md) placement rules (create, list, edit and delete a rule), and
FR-46 in the [chain-placement spec](../../openspec/specs/chain-placement/spec.md) (placing chains by rules), and
[FR-47](../../openspec/specs/placement-rules/spec.md) (apply a rule now).
The map is in [Requirements map](../domain.md#requirements-map).

**Design:** [Components and processes](../architecture.md#components-and-processes), [Layers](../architecture.md#layers),
[Data model](../architecture.md#data-model), [Routes and API](../architecture.md#routes-and-api).

**Decisions:** [ADR 0045](../adr/0045-first-engine-is-local-and-deterministic.md) (the first engine is local and deterministic),
[ADR 0052](../adr/0052-threads-are-formed-by-grouping-a.md) (threads are formed by grouping),
[ADR 0053](../adr/0053-a-counterparty-in-the-tree-is.md) (a counterparty is one address),
[ADR 0054](../adr/0054-on-a-filled-project-is-an.md) (filling again is an explicit rebuild),
[ADR 0055](../adr/0055-similarity-thresholds-are-constants-of-the.md) (thresholds are constants of the engine version),
[ADR 0056](../adr/0056-demo-descriptions-of-and-fixed-in.md) (the demo descriptions),
[ADR 0063](../adr/0063-task-1-5-rules-is-a.md) (rules are a new capability),
[ADR 0064](../adr/0064-when-several-rules-match-a-chain.md) (the more specific rule wins),
[ADR 0065](../adr/0065-rules-apply-on-fill-before-the.md) (rules apply on fill before the engine),
[ADR 0066](../adr/0066-a-rule-targets-a-project-and.md) (a rule targets a project and a thread by name),
[ADR 0070](../adr/0070-applying-a-rule-may-move-chains.md) (applying a rule may move chains),
[ADR 0071](../adr/0071-after-a-rule-is-saved-the.md) (after a rule is saved the page lists the moves),
[ADR 0072](../adr/0072-a-chain-moves-only-when-the.md) (a chain moves only when the rule is its winning rule).

**Related:** [Backend](backend.md) (the layers, the reading loop, the platform layer), [Mail reading](mail-reading.md) (the reply
chains that the engine places), [Rules](rules.md) (the rules that place a chain before the engine), [Auth and accounts](auth.md)
(the caller and the access boundary), [Frontend](frontend.md).

## Modules and their files

The module `backend/app/modules/projects/` uses the layers of [Layers](../architecture.md#layers): the router takes the
service, the service calls the pure rules of `domain.py` and the placer of `placing.py`, and both write through `repository.py`.

| File | What it holds |
|---|---|
| `router.py` | `router` (`/api/v1/projects`), `placements_router` (`/api/v1/placements`) and `ERROR_MAPPING`. A router holds no session and runs no query. |
| `service.py` | `ProjectsService` (`list_projects`, `create`, `get_tree`, `fill`, `list_threads`, `get_location`, `move_chain`, `take_chain_out`, `list_rule_moves`, `apply_rule`), `get_projects_service`, `list_project_names` and `lock_project_names` (the project directory of the rules module), and the two module functions: `place_new_chains`, which the reading run calls after each batch, and `carry_placement`, which the mailboxes module passes as `on_merge` (`backend/app/modules/mailboxes/service.py`). |
| `hand_placing.py` | Placing by hand: `read_location`, `move_chain` and `take_chain_out`. |
| `rule_placing.py` | Placing by rules: `place_by_rules`, which places each candidate by its winning rule and returns the chains that no rule matches, and the thread of a rule (found by name or created). |
| `rule_applying.py` | Applying one rule now: `list_moves`, which lists the chains the rule would move, and `apply_moves`, which moves the chosen ones ([Applying a rule now](#applying-a-rule-now)). |
| `domain.py` | The pure rules: `classify` (the band of a similarity), `choose_thread`, `choose_best_index`, `build_tree`, and the `Band` values. |
| `placing.py` | `Placer`, which stores the engine's placements and new threads of one project, and `ThreadState`, a thread with the documents in it. |
| `repository.py` | The named queries; each one takes the owner's id, locks included. |
| `models.py` | The tables `projects`, `threads` and `chain_placements`, and `PlacementKind` (`engine`, `manual`, `excluded`, `rule`). |
| `schemas.py` | `ProjectCreate`, `ProjectSummary`, `ProjectTree` and the nodes of the tree; `Placement` and `PlacementRuleRef` (the explanation of a placement); `ThreadSummary`, `PlacementMove` and `ChainLocation` for placing by hand; `RuleMoveSource`, `RuleMoveTarget`, `RuleMove` and `RuleMoves` (the moves a rule would make), `RuleApply` and `RuleApplied` (applying them). |
| `errors.py` | `ProjectExists` and `ChainNotInProject`, the domain errors. |

The engine is in `backend/app/platform/placement_engine.py`. The platform imports no module, so the engine knows nothing of projects.

The module reads correspondence only through its service: `list_chain_documents`, `list_chain_facts`, `get_latest_sender_names`
and `has_chain` in `backend/app/modules/correspondence/service.py`, and the types `ChainDocument` and `ChainFacts` of its `schemas.py`. It never
imports the correspondence repository. The other way round, correspondence does not import projects: the mailboxes service
passes `carry_placement` to `store_raw_messages` as `on_merge`, and calls `place_new_chains` after each batch
([Merge hook](#merge-hook)).

## The engine text-1

The engine is `LocalTextEngine` in `backend/app/platform/placement_engine.py`, with `version = "text-1"`. It is a
deterministic local computation with no I/O and no model; it never sees a user id. The app creates it on first use
(`get_placement_engine`, which keeps it in `app.state.placement_engine`).

### What the engine reads

A reply chain is read as a chain document. `build_chain_document` in `backend/app/modules/correspondence/domain.py` joins the
subject of the chain's first email and the texts of its emails, oldest first, one per line. The engine reads the document,
never the emails.

Before scoring, `_terms` turns a text into terms:

- a line is dropped when its first non-space character is `>` (quoted replies);
- the text is lower-cased and `ё` becomes `е`;
- words are the runs of letters and digits;
- words shorter than 2 characters and the stop words are dropped. The stop words are the Russian and the English lists in
  `placement_engine.py`;
- Cyrillic words are stemmed with the Russian Snowball stemmer, ASCII words that are not all digits with the English one;
  other words stay as they are.

The stemmer is pinned in `backend/pyproject.toml`; its version is part of the engine version ([Stack](../tech.md#stack)).

### Scoring

`score(query, documents, corpus)` gives each term the inverse document frequency over the corpus, `ln((1 + N) / (1 + n)) + 1`,
where `N` is the number of corpus documents and `n` the number of them that contain the term. A term that the corpus does not
have gets `ln(1 + N) + 1`. Each text becomes a TF-IDF vector, and the score is the cosine similarity of the query with each
document, rounded to 4 decimals (`SCORE_DECIMALS`).

The corpus is every chain of the user at the time of the run. The same emails, the same description and the same version give
the same scores; a new email in the user's mail changes the weights of the words.

### Bands and the thread rule

`classify` in `backend/app/modules/projects/domain.py` puts a chain's score against a project into one band:

| Score | Band | What is stored |
|---|---|---|
| `>= 0.15` (`sure_threshold`) | threaded | a placement in a thread, by the thread rule |
| `>= 0.05` and `< 0.15` (`lower_threshold`) | unassigned | a placement with no thread: «Неразобранное» |
| `< 0.05` | out | nothing: the chain stays in no project |

The thread rule (`choose_thread`) compares the chain with each thread of the project; a thread's text is the documents of its
chains, joined. The most similar thread takes the chain when its score is at least `0.15` (`thread_threshold`). Ties go to the
earlier thread. Otherwise the chain starts a new thread at the next position, named by the chain's subject.

An engine placement stores the `engine_version` and the similarity it was made with, and the tree shows both. A placement by hand
or by a rule stores neither ([Placing by hand](#placing-by-hand), [Placing by rules](#placing-by-rules)).

### Changing the engine

The three thresholds, the stop words and the stemmer's version belong to the version. Any change that alters `text-1` scores
is a new engine version: a new `version` string and new constants of the engine. That covers the tokenizer, the quoted-line
rule, the `ё` rule, the IDF formula, the thresholds, the stop words and the stemmer version. The reason is the invariant
«Reproducible placement»: the same emails, description and engine version must give the same placement
([ADR 0055](../adr/0055-similarity-thresholds-are-constants-of-the.md)). The thresholds are not app settings, and the module
reads no environment variable. The constants of `text-1` were tuned on the ten demo chains of `docker/greenmail/demo/` and the
three demo descriptions ([ADR 0056](../adr/0056-demo-descriptions-of-and-fixed-in.md)).

A new version re-places nothing by itself. Stored placements keep the version and the similarity they were made with, until the
user presses «Заполнить» on the project ([FR-38](../../openspec/specs/chain-placement/spec.md)). New chains read after the change
are placed by the new version, as the reading run uses the app's engine. Until a fill, one project can hold placements of two
versions, and the tree shows which. A placement by hand is never re-placed by the engine, whatever version is current.

## Placing by rules

A rule places a chain before the engine is asked. The rules are the user's rows of `placement_rules`, described in [Rules](rules.md).
`list_match_rules` in `backend/app/modules/rules/service.py` reads them in the order they win, in the caller's transaction.
`place_by_rules` in `backend/app/modules/projects/rule_placing.py` then goes through the candidates in reading order:

- The winning rule of a candidate is `pick_winning_rule(rules, chain.senders, chain.subject)`: the first rule that matches, by
  address, then by domain, then by subject words ([Matching](rules.md#matching)). A chain with no winning rule goes on to the engine.
- A chain with a winning rule is stored as a placement of kind `rule` in the rule's project. Its thread is the project's first thread
  by position whose name, trimmed and lower-cased, equals the rule's thread name (`find_thread_by_name_for_owner`); when there is none,
  a thread with the rule's name is created at the next position. A rule with no thread name puts the chain in «Неразобранное».
- The placement keeps its own copy of the rule, `rule_condition` and `rule_value` (`add_rule_placement_for_owner`). An edit or a delete
  of the rule later does not change it, and a delete keeps the placement. It stores no similarity and no engine version.

The rules place a chain before the engine, and never a chain placed or taken out by hand:

- **New chains** (`place_new_chains`, after a mailbox read): the rules place first, into any project, filled or not. The chains that no
  rule matches go to the filled projects, as the engine does ([Placing new chains](#placing-new-chains)).
- **A fill** (`ProjectsService.fill`): the project's engine and rule placements are dropped, then the candidates are placed by the rules
  that target this project. A candidate whose winning rule targets another project is left out of this fill, so it is in no project until
  that project is filled or the chain gets a new email. The rest go to the engine. The threads that the rules created or named are among
  the threads of the engine's step.
- **By hand:** a chain with a placement row is never a candidate, so no rule moves a placement by hand or a chain taken out. A move by
  hand replaces a rule placement and clears its rule columns.
- **On a merge** of chains, a placement by hand beats a rule's, and a rule's beats the engine's ([Merge hook](#merge-hook)).

## Applying a rule now

A saved rule places nothing by itself: a placement changes when the user applies the rule. On the page «Правила» the user
gets the list of the chains the rule would move, and «Применить» moves them ([FR-47](../../openspec/specs/placement-rules/spec.md),
[ADR 0070](../adr/0070-applying-a-rule-may-move-chains.md), [ADR 0071](../adr/0071-after-a-rule-is-saved-the.md)). The routes are in
`placements_router` of `backend/app/modules/projects/router.py`; the use cases are `ProjectsService.list_rule_moves` and
`ProjectsService.apply_rule`; the logic is in `rule_applying.py`.

- `GET /api/v1/placements/by-rule/{rule_id}` (signed in) answers `RuleMoves`: `moves`, newest first by `latest_email_at`, then by
  `chain_id`. Each move has `chain_id`, `subject`, `latest_email_at`, `current` (`state` `none` for a chain in no project, or `placed`
  with its `project` and `thread`; the thread is null for «Неразобранное») and `target` (`project`, and `thread_name`, null for
  «Неразобранное»). The route writes nothing.
- `POST /api/v1/placements/by-rule/{rule_id}` takes `RuleApply`: `chain_ids`, at most 5000 ids; a repeated id counts once. It answers
  200 with `RuleApplied`: `moved`, the number of chains moved. The listed ids that no longer qualify are skipped without an error,
  and an unknown id moves nothing.

Another user's or an unknown rule answers 404 `not_found` on both routes.

**Which chains a rule moves** (`_compute_moves`). A chain is a move of a rule when all of these hold:

- the rule is the chain's winning rule, by `pick_winning_rule` and the FR-46 priority ([ADR 0072](../adr/0072-a-chain-moves-only-when-the.md)).
  So a chain that a stronger rule wins is not listed, and a weaker rule's chain is listed for a stronger one that is new;
- the chain has no placement row, or its row is of kind `engine` or `rule`. A chain placed by hand or taken out is never listed;
- the chain is not already in the rule's project and thread. For a rule with no thread name, that is «Неразобранное» of its project.

**Applying** (`apply_moves`) runs in one transaction, after `lock_projects_for_owner` (as the other writes of
[Placing by hand](#placing-by-hand) and [Filling a project](#filling-a-project) do). It recomputes the moves, keeps the ones whose
`chain_id` was sent, deletes each former placement row, places each chain by the rule with `place_by_rules` (only that rule), and
deletes a former thread that is left empty, as a move by hand does. The rule's placement keeps the copy of the rule, as in
[Placing by rules](#placing-by-rules). An applied rule never moves a chain that the rule does not win, so the result equals what
«Заполнить» gives for that rule.

## Filling a project

`POST /api/v1/projects/{project_id}/fill` (signed in) answers 200 with `ProjectTree`. Another user's or an unknown project
answers 404 `not_found`. The SPA button «Заполнить» starts it. When the tree already has chains, the button first asks
«Пересобрать проект? Движок разложит его переписку заново, а цепочки, размещённые вручную, останутся на месте» with the buttons
«Пересобрать» and «Отмена»; a tree with no chains fills at once.

`ProjectsService.fill` runs in one transaction, in this order:

1. It locks every project row of the user (`lock_projects_for_owner`, `FOR UPDATE`, in id order). A fill and a reading batch
   therefore never place the same chain twice.
2. It drops the project's engine and rule placements (`delete_computed_placements_and_unpinned_threads_for_owner`), then the
   project's threads that no placement by hand points to. Placements by hand and the threads holding them stay.
3. It takes the candidates: every chain of the user that has no placement row. Step 2 freed the project's engine and rule chains, so
   they are candidates again; a chain placed by hand or taken out by hand is not.
4. It places the candidates by the rules that target this project, first ([Placing by rules](#placing-by-rules)). A candidate whose
   winning rule targets another project is left out.
5. It scores the rest against the description, with the whole corpus.
6. It places each scored candidate by the bands above. The threaded chains come in reading order and join or start threads. The threads
   that stayed, the ones holding placements by hand, are the first threads of the fill: an engine chain joins the closest of them
   at or above the thread threshold, even when that chain had a thread of its own before.
7. It sets `filled_at` to now and returns the tree.

Reading order is the time of the first email, then its subject, then its key (`reading_order_key` in
`backend/app/modules/correspondence/domain.py`). The chain id is never used, so the order does not depend on the database.

A fill rebuilds the engine's and the rules' placements: the same emails give the same engine placements
([ADR 0054](../adr/0054-on-a-filled-project-is-an.md)). It keeps the placements by hand and their threads, with their names
([ADR 0060](../adr/0060-the-explicit-re-sorting-is-on.md)), and the confirmation says so. A chain taken out by hand is not taken
back by a fill ([ADR 0059](../adr/0059-keeps-the-chain-out-of-every.md)). The engine's chains may join a thread kept by hand
([ADR 0062](../adr/0062-re-sorting-keeps-adding-engine-chains.md)).

## Placing new chains

After each stored batch, the reading run places the chains that got a new email. The steps are in
`_read_folder` in `backend/app/modules/mailboxes/service.py`, and they all run in the batch's transaction:

1. `store_raw_messages` stores the batch, with `on_merge=carry_placement`.
2. It returns the ids of the chains that got a new email in this batch. A copy of an email the user already has is not a new
   email. A chain merged away later in the batch is left out; its survivor is in.
3. `place_new_chains(session, user_id, touched, engine, now)` places them. The folder's `last_uid` is saved in the same
   transaction. If placing raises, the batch and the progress roll back together, and the mailbox is recorded as `failed`
   with `read_failed` ([Reading a mailbox](mail-reading.md#reading-a-mailbox)).

`place_new_chains` locks the user's projects, then returns at once when no chain is touched. Otherwise:

- A candidate is a touched chain with no placement row: in no project and not taken out by hand.
- Each candidate whose winning rule exists is placed by that rule, in the rule's project, filled or not ([Placing by rules](#placing-by-rules)).
- When no project is filled, the other candidates stay in no project. Otherwise each is scored against every filled project. The best
  score takes it; a tie goes to the project created first, then to the name, ignoring case and then exact. The bands and the thread rule
  of [Bands and the thread rule](#bands-and-the-thread-rule) then apply, with the threads of that project as they stand now.
- A chain with a placement row, placed or taken out by hand, is never scored again, so a reply never moves its chain or brings
  back a chain taken out.
- A chain below the lower threshold is not stored. It stays in no project and is scored again only when a new email reaches it,
  or when its user fills a project.

### Merge hook

`_join_chain` in `backend/app/modules/correspondence/service.py` calls the `MergeHook` (`on_merge`) before the emails of the
merged chains move to the survivor. The hook is `carry_placement` in `backend/app/modules/projects/service.py`, called as
`(session, user_id, survivor_id, merged_ids)`. It:

- keeps, among the placements of the survivor and of the merged chains, the winning one: a placement by hand (`manual`) or a
  chain taken out by hand (`excluded`) beats a rule's (`rule`), and a rule's beats the engine's, whatever the dates; among one kind the earliest `placed_at` wins, then
  the project created first, then the name, then the thread's position, with «Неразобранное» last. It drops the other placements
  of these chains ([ADR 0061](../adr/0061-on-a-merge-of-chains-a.md));
- moves the kept placement to the survivor when it belonged to a merged chain.

The merged chains are deleted after the hook. So a merge keeps the chain's place, and a merge never undoes a placement by hand.
The hook is a plain callable passed by the mailboxes module; the correspondence module does not import projects.

## The tree

`GET /api/v1/projects/{project_id}` (signed in) answers 200 with `ProjectTree`. Another user's or an unknown project answers
404 `not_found`. `build_tree` in `backend/app/modules/projects/domain.py` builds the tree on each request; nothing is stored.

- **Counterparties.** Each participant address of the project's chains is a counterparty. A participant is a `From`, `To` or `Cc`
  address other than the user's own ([Mail reading](mail-reading.md#joining-emails-into-reply-chains)). A chain with two
  counterparties shows under both. A chain with none shows under «Без контрагента», which comes last.
- **Names.** A counterparty is named by the display name of the latest email from its address that had one
  (`get_latest_sender_names`); without one, the address is the name. Counterparties are sorted by name, ignoring case, then by address.
- **Threads.** Under a counterparty, its threads come in creation order, and each thread's chains in reading order.
- **«Неразобранное».** The chains with no thread: the chains placed by hand or by a rule first, in reading order, then the engine's
  chains by similarity from high to low, then in reading order (a placement by hand or by a rule has no similarity, and the sort puts it first).
- **Chains.** Each chain has `id`, `subject`, `email_count`, `latest_email_at` and `placement`: `kind` (`engine`, `manual` or `rule`),
  `engine_version` and `similarity`, rounded to 4 decimals; the last two are null for `manual` and `rule`. `rule` is the rule as it
  placed the chain (`condition` and `value`, from the copy in the placement), and it is null unless the kind is `rule`. The SPA shows
  the placement as «Вручную» for a placement by hand, as «Движок text-1 · сходство 43%» for an engine one, and as «Правило · адрес …»,
  «Правило · домен …» or «Правило · слова темы «…»» for a rule (`placementLabel` in `format.ts`).

A chain with two counterparties appears twice in the answer. `threads_of` in `backend/tests/project_trees.py` counts it once.

## Placing by hand

The user places a chain on its page, `/chains/:id`. The block «Проект» (`ChainPlacement.tsx`) shows where the chain is: «<project> → <thread or
Неразобранное> · <Вручную or Движок text-1 · сходство N%>», «Вне проектов» when it is in no project, or «Вне проектов · убрана вручную»
when the user took it out. The button «Убрать из проекта» shows for a placed chain. The form «Перенести» has the selects «Проект» and
«Ветка» (the project's threads, «Неразобранное» and «Новая ветка…») and the field «Название ветки». «Ветка» starts at the chain's current
thread while its own project is selected, and resets to «Неразобранное» when another project is picked
([ADR 0057](../adr/0057-a-chain-is-placed-by-hand.md), [ADR 0058](../adr/0058-by-hand-a-chain-goes-into.md)).

The routes are in `backend/app/modules/projects/router.py` (`placements_router`), the use cases in `hand_placing.py`:

- `GET /api/v1/placements/{chain_id}` (signed in) answers `ChainLocation`: `state` `placed` (with `project`, `thread` and `placement`),
  `none` (in no project, never placed) or `excluded` (taken out by hand).
- `PUT /api/v1/placements/{chain_id}` takes `PlacementMove`: `project_id`, and either `thread_id` (a thread of that project), or
  `new_thread_name` (a new thread, 1 to 100 characters, trimmed), or neither for «Неразобранное». The chain becomes `manual`. Moving
  it into the thread it already holds keeps it there and shows «Вручную» ([FR-40](../../openspec/specs/chain-placement/spec.md)).
  A thread the chain leaves is deleted when no placement points to it any more.
- `DELETE /api/v1/placements/{chain_id}` takes the chain out of its project for good: its row becomes `excluded`, with no project and
  no thread. A chain that is already out, or in no project, answers 409 `chain_not_in_project`. The engine never places an `excluded`
  chain again, by «Заполнить» or after new emails; only a `PUT` places it back ([FR-41](../../openspec/specs/chain-placement/spec.md)).
- `GET /api/v1/projects/{project_id}/threads` (signed in) answers the project's threads in order.

Every route answers 404 `not_found` for another user's chain, project or thread, and for a thread of another project. The move and
the take-out take the project locks first (`lock_projects_for_owner`), in the caller's transaction.

## Listing and creating

- `GET /api/v1/projects` (signed in) answers 200 with the user's projects, each with `id`, `name`, `filled`, `placed_count`
  (chains in a thread) and `unassigned_count` (chains in «Неразобранное»). They are sorted by name, ignoring case, and at most
  `PROJECT_LIST_LIMIT` (200) come back. The list is not paginated.
- `POST /api/v1/projects` (signed in) takes `name` and `description` and answers 201 with the new project: not filled, both counts 0.
  The name and the description are trimmed. A name that differs from one of the user's projects only in letter case answers
  409 `project_exists`.
- No route changes or deletes a project yet.

## Errors over HTTP

| Code | Status | When | Mapped in |
|---|---|---|---|
| `validation_failed` | 422 | a field of `ProjectCreate` is empty, too long, missing or not text; or a field is unknown; or `RuleApply` has more than 5000 `chain_ids` | `ProjectCreate` in `backend/app/modules/projects/schemas.py`; `RequestModel` in `backend/app/platform/validation.py` |
| `project_exists` | 409 | the user already has a project with this name, ignoring case | `ERROR_MAPPING` in `backend/app/modules/projects/router.py` |
| `not_found` | 404 | another user's or an unknown project, chain, thread or rule, on read, fill, placement by hand or applying a rule | `NotFound` (`backend/app/platform/errors.py`) |
| `chain_not_in_project` | 409 | taking out a chain that is already out or in no project | `ERROR_MAPPING` in `backend/app/modules/projects/router.py` |
| `not_signed_in` | 401 | no live session of a confirmed user | `current_user` |
| `forbidden_origin` | 403 | a POST without the app's `Origin` | `OriginGuardMiddleware` |

The field messages, from `schemas.py`:

| Field | Russian message when it fails |
|---|---|
| `name` | «Укажите название проекта»; «Название — не длиннее 100 символов» |
| `description` | «Опишите проект»; «Описание — не длиннее 2000 символов» |
| `new_thread_name` | «Укажите название ветки»; «Название ветки — не длиннее 100 символов»; «Выберите либо ветку, либо новую ветку» (with `thread_id` too) |

`project_exists` reads «Проект с таким названием уже есть».

## The SPA

The pages are in `frontend/src/features/projects/`, behind `RequireUser`: `/projects` (`ProjectsPage`, «Проекты»), `/projects/new`
(`NewProjectPage`, «Новый проект») and `/projects/:id` (`ProjectPage`: the name, the description, «Заполнить» and the tree). The start
page links to «Проекты». `format.ts` holds the plural labels of the counts (for example «1 цепочка», «2 цепочки», «5 цепочек») and
`placementLabel`. The chain page (`/chains/:id`) shows the «Проект» block of its chain, from `frontend/src/features/projects/ChainPlacement.tsx`;
it places the chain by hand as described in [Placing by hand](#placing-by-hand). The page `/rules` is described in [Rules](rules.md#the-spa). A project page whose tree has no counterparties and no «Неразобранное» shows «Подходящей переписки не нашлось:
уточните описание» when the project is filled, and «Проект пуст: нажмите «Заполнить», чтобы найти его переписку» when it is not.

## Test seams

- **`FakePlacementEngine`** (`backend/app/platform/placement_engine.py`) takes a version, a dict of scores and its own thresholds
  (`sure=0.3`, `lower=0.15`, `thread=0.3` by default). A document scores the highest value of a key that occurs in both the query
  and the document, ignoring case; otherwise 0. It ignores the corpus. Its thresholds are its own, not those of `text-1`.
- **The fill route** takes the engine from `get_placement_engine`. `use_engine(app, engine)` in `backend/tests/project_trees.py`
  sets `app.dependency_overrides[get_placement_engine]`.
- **The reading run** takes the engine as an argument: `read_due_mailboxes(database, reader, clock, settings, engine=None)`
  uses `LocalTextEngine()` when it gets none. The dependency override does not reach it. The factories' `read_due(engine=None)`
  passes the engine on. A test that places new chains passes its engine to `read_due`.
- **`backend/tests/project_trees.py`** holds the helpers of the project suites: `letter()` builds a raw email with Message-ID
  `<p{n}@stroymaster.example>`, and a reply names the number it answers; `put()` puts one into the inbox; `load_demo_mail()`
  loads the demo `.eml` files as `manifest.json` lists them, with the `logins` and `newest_first` options;
  `signed_in_with_mailbox()` and `vera_with_mailbox()` sign in with a mailbox connected; `list_projects()`, `open_project()` and
  `fill_project()` call the routes. `threads_of()` keys the threads by id and counts a chain once; `thread_subjects()`,
  `placed_chains()` and `all_subjects()` read the chains' subjects; `tree_snapshot()` reads the threads and «Неразобранное»
  without ids. `DEMO_PROJECTS` holds the three demo descriptions, keyed by the names `RENOVATION`, `PURCHASE` and `CONFERENCE`.
- **`Factories.create_project(client, name, description)`** in `backend/tests/factories.py` creates a project through the API and
  asserts 201. The same file has the placement route helpers `move_chain`, `move_chain_response`, `take_out_chain`,
  `take_out_chain_response`, `chain_location` and `project_threads`.
- **`backend/tests/hand_placement.py`** holds the helpers of the placement-by-hand suites: `anna_with_chains()` reads one chain per
  subject, and `chain_in_tree()` finds a chain in a tree (a thread or «Неразобранное»).
- **`backend/tests/rule_support.py`** holds the helpers of the placement-rule suites: `by_rule()` builds the expected `Placement` of a
  rule placement, `by_engine()` the engine's, `read_again()` reads new chains, and `anna_with_two_projects()` seeds the two-project fixture.
  `rule_moves()` and `apply_rule()` call the two routes of [Applying a rule now](#applying-a-rule-now), and `rule_moves_response()`
  and `apply_rule_response()` return the raw responses.
  `create_rule()` and `create_rule_response()` in `backend/tests/factories.py` post a rule.

## Tests

- Unit tests: `backend/app/platform/test_placement_engine.py` (the engine `text-1`, the fake, and the demo chains), and
  `backend/app/modules/rules/test_domain.py` (the matching of rules, in [Rules](rules.md#tests)).
- Integration tests, through HTTP against the test database, one file per group: `test_projects_create_list.py` (FR-32, FR-33),
  `test_projects_tree.py` (FR-34), `test_projects_fill.py` (FR-35, FR-36), `test_placement_explained.py` (FR-37, FR-38) and
  `test_placement_new_chains.py` (FR-39), `test_placement_by_hand.py` (FR-40), `test_placement_taken_out.py` (FR-41) and
  `test_placement_kept.py` (FR-42). The placing-by-rules groups are `test_placement_by_rules.py` (FR-46) and
  `test_placement_rules_with_engine.py` (rules next to the engine); the rules CRUD is `test_rules_crud.py` (FR-43 to FR-45).
  Applying a rule now is tested in `test_placement_apply_rule.py` (FR-47, and FR-46 for a new rule that moves nothing),
  `test_placement_apply_rule_edits.py` (FR-47 after an edit, FR-45) and `test_placement_apply_rule_requests.py` (FR-47 requests:
  order, repeated ids, another user's rule, malformed body, the route guards).
- `just test` runs the unit tests, `just test-db` the integration tests, `just test-all` both. The database setup is in
  [Integration tests](backend.md#integration-tests).

## Changing it safely

- **A threshold, a stop word or the stemmer's version:** make a new engine version with its own `version` string and constants
  ([Changing the engine](#changing-the-engine)). Never edit the constants of `text-1` in place: placements store their version,
  and the same version must give the same placement ([ADR 0055](../adr/0055-similarity-thresholds-are-constants-of-the.md)).
- **A behavior** (the bands, the thread rule, the order of the tree, what a fill does, the placing by rules): the behavior changes, so it goes through the
  spec first ([projects spec](../../openspec/specs/projects/spec.md), [chain-placement spec](../../openspec/specs/chain-placement/spec.md)),
  with the user's approval, then the code, the tests and this article.
- **One engine per run.** The reading loop gets its engine from `create_app` (`backend/app/main.py`), the fill route from
  `get_placement_engine`, and `read_due_mailboxes` defaults to `LocalTextEngine()`. A new engine is wired into all three, or the fill
  and the reading run place by different versions.
- **The merge hook** must run inside the caller's transaction and before the merged chains are deleted, and it must keep the rule of
  [Merge hook](#merge-hook).
- **The locks.** Code that places chains takes `lock_projects_for_owner` first, as `fill`, `place_new_chains` and the placement
  by hand do. The rule writes that add or retarget a rule (create and edit) take it too ([Rules](rules.md#use-cases)); a delete does not.
  Applying a rule takes it too ([Applying a rule now](#applying-a-rule-now)).
- **The owner.** Every repository query takes the owner's id, and a route takes its caller from `current_user`
  ([Auth and accounts](auth.md#access-boundary) describes the boundary).
- **The tables.** A change of a table is a new revision in `backend/migrations/versions/`, from `script.py.mako`; the revision
  `0005` to `0007` stay as they are ([Migrations](backend.md#migrations)).
- **Email text** is never logged. The tree answer carries subjects and counts, not email texts ([Mail reading](mail-reading.md)).
