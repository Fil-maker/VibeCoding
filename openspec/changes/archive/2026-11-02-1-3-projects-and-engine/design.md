# Design

## Context

After task 1.2 the backend has the modules `accounts`, `auth`, `health`, `mailboxes` and
`correspondence`: emails stored once per user and joined into reply chains, a background reading loop
that stores each batch of 50 emails in its own transaction, and chain merging that keeps the oldest
stored chain (`docs/architecture.md`). No project, thread or placement exists yet. Rules that shape this
change: the analysis engine is a collaborator reached through a dependency factory and placements store
the engine version (`.claude/rules/server-architecture.md`); the owner filter on every query
(`.claude/rules/data-access.md`); tests are deterministic and use no network
(`.claude/rules/testing.md`). User decisions of this change and before it: a local deterministic engine
(ADR 0045); two thresholds — thread, «Неразобранное», out; threads by mutual similarity named by the
earliest chain's subject; a counterparty is one address; «Заполнить» on a filled project rebuilds it; a
chain belongs to at most one project (ADR 0034); the engine never moves a placed chain (ADR 0030).

## Goals / Non-Goals

**Goals:**
- One placement rule for both paths: filling a project and placing a new chain use the same similarity,
  thresholds and thread grouping, so a new chain lands where a fill would have put it.
- Reproducibility independent of storage: no random ids, creation order or wall clock enter the
  engine's decisions.
- Every placement row carries its kind, similarity and engine version, ready for task 1.4's kinds
  «by hand» and «by a rule».

**Non-Goals:**
- Placement by hand, rules, re-sorting that keeps manual placements (task 1.4).
- Editing or deleting a project; references to a chain in a second project.
- A third-party model, consent, background filling of very large mailboxes.

## Decisions

### Modules

- `projects` — projects, threads, placements, the tree, «Заполнить» and `place_new_chains`. It reads
  chains, their emails and participants only through the `correspondence` service.
- `platform/placement_engine.py` — the `PlacementEngine` protocol, `LocalTextEngine` (version
  `text-1`), `FakePlacementEngine` and the dependency factory `get_placement_engine`. Pure computation,
  no I/O; it never sees a user id.
- `mailboxes` passes the engine to `projects.service.place_new_chains` after each stored batch.

Alternative: the engine inside `projects/domain.py`. Rejected: the rules treat the engine as a
collaborator behind a factory, and a later third-party engine must replace it without touching
placement logic.

### Similarity (user decision: local, deterministic)

A chain's document is its first subject plus the text of its emails oldest first; lines starting with
`>` (quoted replies) are dropped. Words are lower-cased, `ё` becomes `е`, stop words are dropped and
each word is cut to its stem by the Snowball stemmer (Russian for Cyrillic words, English for Latin).
The similarity of two documents is the cosine of their TF-IDF vectors; IDF is computed over all the
user's chains at that moment, so it does not depend on which chains are already in other projects. The
description is a document of its own. Floats are rounded to 4 decimals before any comparison, so ties
are decided by the tie rules below and not by float noise.

Alternatives: plain word overlap (Jaccard) — rejected, common business words dominate; scikit-learn —
rejected, a heavy dependency for a few hundred lines of arithmetic; a hand-written suffix stripper —
rejected, Snowball is the known stemmer for Russian and is small and pure Python.

### Thresholds belong to the engine version

`text-1` fixes three constants: the sure threshold, the lower threshold and the thread threshold. They
are tuned in the code step on the demo mail, so that its ten chains fall into three projects described
as in `docker/greenmail/demo/` and nothing else, then frozen. Any change of a threshold, a stop word or
the stemmer's version is a new engine version (`text-2`).

User decision at approval, replacing the earlier answer «пороги задаются настройками приложения»: an
env setting would change placements without changing the version, which breaks «Reproducible
placement» (the same version must give the same result).

### Filling a project (FR-35, FR-36)

In one transaction, under a lock of all the user's project rows (`FOR UPDATE`), so a fill and the
reading loop never place the same chain twice:

1. Drop the project's threads and its engine placements (a first fill has none).
2. Candidates: the user's chains with no placement. Score each against the description.
3. Below lower → skipped. Lower ≤ s < sure → «Неразобранное». Sure ≤ s → threaded.
4. Threaded chains in reading order: the first email's `sent_at`, then the first subject, then the
   email key — never the chain id. Each chain joins the existing thread with the highest similarity to
   the thread's document (all its chains' documents joined) if it reaches the thread threshold, ties to
   the earlier thread; else it starts a new thread named by its first subject.
5. Mark the project filled (`filled_at`).

The answer is the new tree; an empty filled project makes the page show «Подходящей переписки не
нашлось: уточните описание».

### Placing new chains (FR-39)

`store_raw_messages` returns the ids of the chains that got a new email. In the same transaction as
the batch, `place_new_chains` takes those that have no placement, scores each against the description
of every filled project of the user, picks the highest (ties: the project created first, then by name)
and applies steps 3–4 against that project's existing threads. Placed chains are never read for
placement, so a reply never moves its chain. A user without filled projects costs one query.

### Merged chains keep the first placement

When an email joins chains (FR-29), `correspondence` moves the emails into the oldest stored chain
and deletes the others, which would cascade their placements. Before deleting, it calls a hook given by
the caller: `projects.service.carry_placement(survivor, merged)` keeps on the survivor the placement
with the earliest `placed_at` among all of them and drops the rest. The `mailboxes` service wires the
hook, so `correspondence` does not import `projects`.

Alternative: keep the survivor's placement always. Rejected: the survivor is decided by storage order,
which can drop a placement the user has seen for longer.

### The tree (FR-34)

Built per request from the placements, the chains' participants and their latest sender names:
counterparties by name case-insensitively, then address, «Без контрагента» last; threads in their
creation order (step 4); chains in a thread by the first email's `sent_at`; «Неразобранное» by
similarity descending, then `sent_at`. A counterparty's name is the display name of the latest email
sent from that address, else the address.

### Data model (revision `0005`)

- `projects`: `id`, `user_id` → users (cascade), `name` varchar(100), `description` text,
  `filled_at` timestamptz null, `created_at`; unique index on (`user_id`, `lower(name)`).
- `threads`: `id`, `user_id`, `project_id` → projects (cascade), `name` text, `position` int,
  `created_at`; unique (`project_id`, `position`).
- `chain_placements`: `chain_id` PK → reply_chains (cascade), `user_id`, `project_id` → projects
  (cascade), `thread_id` → threads null (null is «Неразобранное»), `kind` varchar(16) with a check
  `kind in ('engine')` (task 1.4 widens it), `similarity` numeric(5,4), `engine_version` varchar(32),
  `placed_at` timestamptz; index on (`user_id`, `project_id`).

The primary key on `chain_id` enforces «a chain belongs to at most one project».

## Interface

The public contract for tests and code. Paths are under `/api/v1`; every route needs a signed-in user
(else 401 `not_signed_in`); state-changing routes need a matching `Origin` (else 403
`forbidden_origin`). Another user's id answers 404 `not_found`.

### Schemas

- `ProjectCreate` (request): `{name: str 1–100, description: str 1–2000}`, both stripped
- `ProjectSummary`: `{id: uuid, name: str, filled: bool, placed_count: int, unassigned_count: int}`
- `Placement`: `{kind: "engine", engine_version: str, similarity: float}` — `similarity` 0–1, 4 decimals
- `PlacedChain`: `{id: uuid, subject: str, email_count: int, latest_email_at: datetime, placement: Placement}`
- `ThreadNode`: `{id: uuid, name: str, chains: PlacedChain[]}`
- `CounterpartyNode`: `{address: str | null, name: str, threads: ThreadNode[]}` — `address` null is «Без контрагента»
- `ProjectTree`: `{id: uuid, name: str, description: str, filled: bool, counterparties: CounterpartyNode[], unassigned: PlacedChain[]}`

### Routes

| Route | Body | Success | Errors |
|---|---|---|---|
| `GET /projects` | — | 200 `ProjectSummary[]` by name, at most 200 | — |
| `POST /projects` | `ProjectCreate` | 201 `ProjectSummary` | 409 `project_exists`, 422 `validation_failed` |
| `GET /projects/{id}` | — | 200 `ProjectTree` | 404 `not_found` |
| `POST /projects/{id}/fill` | — | 200 `ProjectTree` | 404 `not_found` |

The confirmation of FR-36 is the SPA's; the route always rebuilds.

### Error messages (Russian, exact)

| Code | Message |
|---|---|
| `project_exists` | «Проект с таким названием уже есть» |
| field messages | «Укажите название проекта», «Название — не длиннее 100 символов», «Опишите проект», «Описание — не длиннее 2000 символов» |

### Service functions used by tests

- `app.modules.mailboxes.service.read_due_mailboxes(database, reader, clock, settings, engine: PlacementEngine = LocalTextEngine())` — as in task 1.2, now placing new chains.

### Platform interface

- `PlacementEngine` protocol: `version: str`, `sure_threshold: float`, `lower_threshold: float`,
  `thread_threshold: float`, `score(query: str, documents: Sequence[str], corpus: Sequence[str]) -> list[float]`
  — the similarity of `query` to each document, 4 decimals, IDF over `corpus`.
- `LocalTextEngine()` — version `text-1`.
- `FakePlacementEngine(version: str, scores: Mapping[str, float], sure: float = 0.3, lower: float = 0.15, thread: float = 0.3)` —
  `score` gives a document the highest value among the keys found in both the query and the document
  (case-insensitive substring), else 0.0.
- `get_placement_engine(request) -> PlacementEngine`, lazy, overridden in tests.

### SPA pages

- Start page: a link «Проекты» (`/projects`) beside «Почтовые ящики» and «Переписка».
- «Проекты» (`/projects`): rows of name, «N цепочка/цепочки/цепочек», «N неразобранная/неразобранные/неразобранных» when not zero; the button «Создать проект»; empty: «Проектов пока нет: создайте первый».
- «Новый проект» (`/projects/new`): «Название», «Описание», button «Создать»; field and conflict errors of «Error messages»; success opens the project.
- Project (`/projects/:id`): name, description, button «Заполнить»; the tree of counterparties (name and address), threads, chains (subject linking to `/chains/:id`, «N письмо/письма/писем», date `dd.mm.yyyy`, «Движок <version> · сходство <N>%»); the section «Неразобранное»; empty and never filled: «Проект пуст: нажмите «Заполнить», чтобы найти его переписку»; filled and empty: «Подходящей переписки не нашлось: уточните описание». On a project with chains «Заполнить» asks «Пересобрать проект? Движок разложит его переписку заново» with «Пересобрать» and «Отмена». While filling the button shows «Заполняется…». Unknown id: «Страница не найдена».

### Test seams

- `get_placement_engine` → `FakePlacementEngine` for exact similarities and versions (FR-37, FR-38
  version change); `LocalTextEngine` itself for the demo-like scenarios of FR-35 and FR-39 and its own
  unit tests (determinism, order independence, stems).
- `read_due_mailboxes` with `FakeMailReader` and the `engine` argument, as in task 1.2.
- Raw emails from `backend/tests/mail_factory.py`; a factory in `backend/tests/factories.py` that
  creates a project through the API.

## Risks / Trade-offs

- [The demo-tuned thresholds misplace real mail] → «Неразобранное» catches the middle band; task 1.4
  lets the user fix placements; a better engine is a new version.
- [Fill and placement recompute IDF over all the user's chains] → fine for a year of one person's mail;
  if it gets slow, a stored term index is a later technical item.
- [A new batch placed before the rest of a large first read] → placement is per batch and order
  independent only for fills; noted, the user can fill again.
- [A merge hook couples `correspondence` to its caller] → a plain callable argument, no import.

## Migration Plan

Revision `0005` only creates `projects`, `threads` and `chain_placements`; users, mailboxes, emails
and chains are untouched. Downgrade to `0004` drops the three tables, losing projects and placements
only. New dependency `snowballstemmer` with an exact pin (its version is part of the engine version).
No new env vars.
