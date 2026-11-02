# Projects

Updated 02.11.2026

**Code:** `backend/app/modules/projects/` (`router.py`, `service.py`, `domain.py`, `placing.py`, `repository.py`, `models.py`,
`schemas.py`, `errors.py`), the platform file `backend/app/platform/placement_engine.py`, its unit tests
`backend/app/platform/test_placement_engine.py`, the wiring in `backend/app/modules/mailboxes/service.py`, the functions of
`backend/app/modules/correspondence/service.py` that projects use and its `MergeHook`, the migration
`backend/migrations/versions/0005_projects_and_placements.py`, the integration tests `backend/tests/integration/test_projects_*.py`
and `test_placement_*.py`, and the test seams `backend/tests/project_trees.py` and `Factories.create_project` in
`backend/tests/factories.py`.

**Requirements:** [FR-32 … FR-34](../../openspec/specs/projects/spec.md) projects (create, list, show as a tree),
[FR-35 … FR-39](../../openspec/specs/chain-placement/spec.md) chain placement (fill, fill again, every placement explained,
reproducible placement, placing new chains). The map is in [Requirements map](../domain.md#requirements-map).

**Design:** [Components and processes](../architecture.md#components-and-processes), [Layers](../architecture.md#layers),
[Data model](../architecture.md#data-model), [Routes and API](../architecture.md#routes-and-api).

**Decisions:** [ADR 0045](../adr/0045-first-engine-is-local-and-deterministic.md) (the first engine is local and deterministic),
[ADR 0052](../adr/0052-threads-are-formed-by-grouping-a.md) (threads are formed by grouping),
[ADR 0053](../adr/0053-a-counterparty-in-the-tree-is.md) (a counterparty is one address),
[ADR 0054](../adr/0054-on-a-filled-project-is-an.md) (filling again is an explicit rebuild),
[ADR 0055](../adr/0055-similarity-thresholds-are-constants-of-the.md) (thresholds are constants of the engine version),
[ADR 0056](../adr/0056-demo-descriptions-of-and-fixed-in.md) (the demo descriptions).

**Related:** [Backend](backend.md) (the layers, the reading loop, the platform layer), [Mail reading](mail-reading.md) (the reply
chains that the engine places), [Auth and accounts](auth.md) (the caller and the access boundary), [Frontend](frontend.md).

## Modules and their files

The module `backend/app/modules/projects/` uses the layers of [Layers](../architecture.md#layers): the router takes the
service, the service calls the pure rules of `domain.py` and the placer of `placing.py`, and both write through `repository.py`.

| File | What it holds |
|---|---|
| `router.py` | `router` (`/api/v1/projects`) and `ERROR_MAPPING`. A router holds no session and runs no query. |
| `service.py` | `ProjectsService` (`list_projects`, `create`, `get_tree`, `fill`), `get_projects_service`, and the two module functions: `place_new_chains`, which the reading run calls after each batch, and `carry_placement`, which correspondence calls as `on_merge`. |
| `domain.py` | The pure rules: `classify` (the band of a similarity), `choose_thread`, `choose_best_index`, `build_tree`, and the `Band` values. |
| `placing.py` | `Placer`, which stores the engine's placements and new threads of one project, and `ThreadState`, a thread with the documents in it. |
| `repository.py` | The named queries; each one takes the owner's id, locks included. |
| `models.py` | The tables `projects`, `threads` and `chain_placements`, and `PlacementKind`. |
| `schemas.py` | `ProjectCreate`, `ProjectSummary`, `ProjectTree` and the nodes of the tree. |
| `errors.py` | `ProjectExists`, the one domain error. |

The engine is in `backend/app/platform/placement_engine.py`. The platform imports no module, so the engine knows nothing of projects.

The module reads correspondence only through its service: `list_chain_documents`, `list_chain_facts` and `get_latest_sender_names`
in `backend/app/modules/correspondence/service.py`, and the types `ChainDocument` and `ChainFacts` of its `schemas.py`. It never
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

Every placement stores the `engine_version` and the similarity it was made with. The tree shows both.

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
versions, and the tree shows which. Manual placements arrive with task 1.4 and are not built yet.

## Filling a project

`POST /api/v1/projects/{project_id}/fill` (signed in) answers 200 with `ProjectTree`. Another user's or an unknown project
answers 404 `not_found`. The SPA button «Заполнить» starts it. When the tree already has chains, the button first asks
«Пересобрать проект? Движок разложит его переписку заново» with the buttons «Пересобрать» and «Отмена»; a tree with no chains
fills at once.

`ProjectsService.fill` runs in one transaction, in this order:

1. It locks every project row of the user (`lock_projects_for_owner`, `FOR UPDATE`, in id order). A fill and a reading batch
   therefore never place the same chain twice.
2. It drops the project's threads and its engine placements.
3. It takes the candidates: every chain of the user that is in no project now. Step 2 freed the project's own chains, so they
   are candidates again.
4. It scores each candidate against the description, with the whole corpus.
5. It places each candidate by the bands above. The threaded chains come in reading order and join or start threads; the
   threads of a fill start empty.
6. It sets `filled_at` to now and returns the tree.

Reading order is the time of the first email, then its subject, then its key (`reading_order_key` in
`backend/app/modules/correspondence/domain.py`). The chain id is never used, so the order does not depend on the database.

A fill is a rebuild: it keeps nothing of the project's earlier placements, and the same emails give the same tree
([ADR 0054](../adr/0054-on-a-filled-project-is-an.md)). Today every placement is an engine placement. Task 1.4 makes a fill keep
manual placements; that is not built yet.

## Placing new chains

After each stored batch, the reading run places the chains that got a new email. The steps are in
`_read_folder` in `backend/app/modules/mailboxes/service.py`, and they all run in the batch's transaction:

1. `store_raw_messages` stores the batch, with `on_merge=carry_placement`.
2. It returns the ids of the chains that got a new email in this batch. A copy of an email the user already has is not a new
   email. A chain merged away later in the batch is left out; its survivor is in.
3. `place_new_chains(session, user_id, touched, engine, now)` places them. The folder's `last_uid` is saved in the same
   transaction. If placing raises, the batch and the progress roll back together, and the mailbox is recorded as `failed`
   with `read_failed` ([Reading a mailbox](mail-reading.md#reading-a-mailbox)).

`place_new_chains` locks the user's projects. It returns at once when no project is filled or no chain is touched. Otherwise:

- A candidate is a touched chain that is in no project.
- Each candidate is scored against every filled project. The best score takes it; a tie goes to the project created first, then
  to the name, ignoring case and then exact. The bands and the thread rule of [Bands and the thread rule](#bands-and-the-thread-rule)
  then apply, with the threads of that project as they stand now.
- A chain that is already in a project is never scored again, so a reply never moves its chain.
- A chain below the lower threshold is not stored. It stays in no project and is scored again only when a new email reaches it,
  or when its user fills a project.

### Merge hook

`_join_chain` in `backend/app/modules/correspondence/service.py` calls the `MergeHook` (`on_merge`) before the emails of the
merged chains move to the survivor. The hook is `carry_placement` in `backend/app/modules/projects/service.py`, called as
`(session, user_id, survivor_id, merged_ids)`. It:

- keeps, among the placements of the survivor and of the merged chains, the one made earliest (`placed_at`, then the project
  created first, then the name, then the thread's position, with «Неразобранное» last), and drops the other placements of
  these chains;
- moves the kept placement to the survivor when it belonged to a merged chain.

The merged chains are deleted after the hook. So a merge keeps the chain's place, and a chain already in a project is never moved.
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
- **«Неразобранное».** The chains with no thread, by similarity from high to low, then in reading order.
- **Chains.** Each chain has `id`, `subject`, `email_count`, `latest_email_at` and `placement`: `kind` (`engine`),
  `engine_version` and `similarity`, rounded to 4 decimals. The SPA shows the placement as «Движок text-1 · сходство 43%».

A chain with two counterparties appears twice in the answer. `threads_of` in `backend/tests/project_trees.py` counts it once.

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
| `validation_failed` | 422 | a field of `ProjectCreate` is empty, too long, missing or not text; or a field is unknown | `ProjectCreate` in `backend/app/modules/projects/schemas.py`; `RequestModel` in `backend/app/platform/validation.py` |
| `project_exists` | 409 | the user already has a project with this name, ignoring case | `ERROR_MAPPING` in `backend/app/modules/projects/router.py` |
| `not_found` | 404 | another user's or an unknown project, on read or fill | `NotFound` (`backend/app/platform/errors.py`) |
| `not_signed_in` | 401 | no live session of a confirmed user | `current_user` |
| `forbidden_origin` | 403 | a POST without the app's `Origin` | `OriginGuardMiddleware` |

The field messages, from `schemas.py`:

| Field | Russian message when it fails |
|---|---|
| `name` | «Укажите название проекта»; «Название — не длиннее 100 символов» |
| `description` | «Опишите проект»; «Описание — не длиннее 2000 символов» |

`project_exists` reads «Проект с таким названием уже есть».

## The SPA

The pages are in `frontend/src/features/projects/`, behind `RequireUser`: `/projects` (`ProjectsPage`, «Проекты»), `/projects/new`
(`NewProjectPage`, «Новый проект») and `/projects/:id` (`ProjectPage`: the name, the description, «Заполнить» and the tree). The start
page links to «Проекты». `format.ts` holds the plural labels of the counts (for example «1 цепочка», «2 цепочки», «5 цепочек») and
`placementLabel`. A project page whose tree has no counterparties and no «Неразобранное» shows «Подходящей переписки не нашлось:
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
  asserts 201.

## Tests

- Unit tests: `backend/app/platform/test_placement_engine.py` (the engine `text-1`, the fake, and the demo chains).
- Integration tests, through HTTP against the test database, one file per group: `test_projects_create_list.py` (FR-32, FR-33),
  `test_projects_tree.py` (FR-34), `test_projects_fill.py` (FR-35, FR-36), `test_placement_explained.py` (FR-37, FR-38) and
  `test_placement_new_chains.py` (FR-39).
- `just test` runs the unit tests, `just test-db` the integration tests, `just test-all` both. The database setup is in
  [Integration tests](backend.md#integration-tests).

## Changing it safely

- **A threshold, a stop word or the stemmer's version:** make a new engine version with its own `version` string and constants
  ([Changing the engine](#changing-the-engine)). Never edit the constants of `text-1` in place: placements store their version,
  and the same version must give the same placement ([ADR 0055](../adr/0055-similarity-thresholds-are-constants-of-the.md)).
- **A rule** (the bands, the thread rule, the order of the tree, what a fill does): the behavior changes, so it goes through the
  spec first ([projects spec](../../openspec/specs/projects/spec.md), [chain-placement spec](../../openspec/specs/chain-placement/spec.md)),
  with the user's approval, then the code, the tests and this article.
- **One engine per run.** The reading loop gets its engine from `create_app` (`backend/app/main.py`), the fill route from
  `get_placement_engine`, and `read_due_mailboxes` defaults to `LocalTextEngine()`. A new engine is wired into all three, or the fill
  and the reading run place by different versions.
- **The merge hook** must run inside the caller's transaction and before the merged chains are deleted, and it must keep the rule of
  [Merge hook](#merge-hook).
- **The locks.** Code that places chains takes `lock_projects_for_owner` first, as `fill` and `place_new_chains` do.
- **The owner.** Every repository query takes the owner's id, and a route takes its caller from `current_user`
  ([Auth and accounts](auth.md#access-boundary) describes the boundary).
- **The tables.** A change of a table is a new revision in `backend/migrations/versions/`, from `script.py.mako`; the revision
  `0005` stays as it is ([Migrations](backend.md#migrations)).
- **Email text** is never logged. The tree answer carries subjects and counts, not email texts ([Mail reading](mail-reading.md)).
