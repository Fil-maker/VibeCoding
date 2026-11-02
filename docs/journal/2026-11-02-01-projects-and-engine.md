# Projects and the engine

Date: 02.11.2026 · Task: 1.3 · Change: 1-3-projects-and-engine

## Goal

A user creates a project with a description. «Заполнить» lays out the project's reply chains as a tree
(counterparty → thread), puts unsure chains into «Неразобранное», and after every mailbox reading new
chains take their place by themselves. Two new capabilities: `projects` (FR-32…FR-34) and
`chain-placement` (FR-35…FR-39). Out of scope (left to `docs/ideas.md`): manual placement and rules
(task 1.4), editing and deleting a project, a chain linked into a second project, merging addresses, a
third-party model. Four product invariants are touched (explainable, reproducible, history kept, access
boundary); none is weakened.

## What was done

- Design in the first session: the path «Новая возможность», the proposal, two new delta specs, design
  and tasks; `openspec validate --strict` passed; the plan row got FR-32…FR-39 and the plan edition 0.9.
- Slice 1, engine and schema: the local engine `text-1` in `backend/app/platform/placement_engine.py`
  (TF-IDF and cosine, Snowball stemmer, new dependency `snowballstemmer==3.0.1`), a fake engine for
  tests, a dependency factory, and migration `0005` with `projects`, `threads`, `chain_placements`.
  Thresholds tuned on the demo mail: sure 0.15, lower 0.05, thread 0.15. The weakest demo margin is
  «Выбор дизайна переговорной» at 0.153.
- Slice 2, backend FR-32…FR-39: create and list projects, the tree, «Заполнить», placing new chains
  after every mailbox reading. Groups 3 and 4 ran as one cycle, because the tree is reachable only
  through «Заполнить».
- Slice 3, SPA: pages «Проекты», «Новый проект» and the project page with the tree, the question before
  a rebuild, a link from the start page.
- Manual checks 7.3-7.5 passed in the built-in browser on the dev stack with the demo mail: «Ремонт
  офиса» gave four chains, «Закупка техники» and «Конференция ТехФорум» three each, every demo chain in
  exactly one project, «Отмена» left the tree, «Пересобрать» gave the same tree with new placement
  times, and a reply added by `just demo-mail add-new` stayed in its chain (6 emails, date 30.10.2026).
- Finish: change archived to `openspec/changes/archive/2026-11-02-1-3-projects-and-engine/`, specs
  merged, requirements map updated, ADRs 0052-0056 written, guide page `docs/guide/projects.md` and
  other implementation docs written through `/document`.
- Final checks: `just check` clean; tests backend unit 90, db 188, frontend 122; `alembic check` clean.
- Invariant review findings accepted and fixed: the engine was created at import as a default argument
  of `read_due_mailboxes` (now lazy), a docstring wording, leftover Alembic comments.
- Review findings dropped, with the reason: corpus-dependent similarity for new chains (accepted risk in
  the design «Risks»); the thread-delete cascade and the merge rule for future manual placements (a
  task 1.4 concern); unbounded internal list reads (the tree and IDF need all rows); schema imports
  from correspondence (service result types).

## Key questions to the AI

- Which path for 1.3? Answer chosen: «Новая возможность (рекомендую)».
- How does the engine decide a chain belongs to a project, how does it build threads, who is a
  counterparty, and what does «Заполнить» do on a filled project? Chosen: «Два порога (рекомендую)»,
  «Группировка по сходству (рекомендую)», «Адрес (рекомендую)», «Пересобирает заново (рекомендую)».
- Keep the plan row 1.3 unchanged? «Да, как есть (рекомендую)».
- Similarity thresholds: constants of the engine version or app settings? «Константы версии
  (рекомендую)»; the AI had flagged this as a deviation from the user's earlier answer, because an
  environment setting would change placement without changing the version. The deltas were approved
  with «Да (рекомендую)».
- Which decisions go to ADRs? «3, 4, 5, 6, 8 (рекомендую)».
- Test-writing from a worktree session: the AI offered a separate session for `test-writer` or a `/fix`
  of the sandbox first; the user chose the separate session (recorded in the handoff).

## Decisions

| Decision | Alternatives | Reason | Who |
| --- | --- | --- | --- |
| Threads are formed by grouping a project's chains by mutual similarity above a threshold; a thread is named by the subject of its earliest chain; a new chain joins the closest thread or starts a new one | one thread per subject | Пользователь выбрал «Группировка по сходству» | [human] |
| A counterparty in the tree is one participant address, named from the emails; merging addresses stays the idea «Counterparty with several addresses» | by domain except public mail domains | Пользователь выбрал «Адрес» | [human] |
| «Заполнить» on a filled project is an explicit user action with confirmation that rebuilds the engine's placements of the project from the same emails and gives the same tree; task 1.4 makes it keep manual placements | only an empty project can be filled | Пользователь выбрал «Пересобирает заново» | [human] |
| Similarity thresholds are constants of the engine version (text-1), tuned on the demo mail and frozen; any change of a threshold, stop word or stemmer version is a new engine version; supersedes «thresholds are app settings» | app settings stored with each placement | Пользователь выбрал «Константы версии»: env-настройка меняла бы раскладку без смены версии и ломала воспроизводимость | [human] |
| Demo descriptions of «Закупка техники» and «Конференция ТехФорум» fixed in the slice-1 brief for tuning text-1 | - | tasks 1.3 and 7.4 need three demo descriptions; only «Ремонт офиса» had one in FR-35 | [AI → accepted] |

## Mistakes and lessons

- The demo descriptions of two of the three demo projects were not in the artifacts; the AI wrote them
  into the slice-1 brief itself (decision above).
- The thresholds were first chosen by the user as app settings; the AI saw that this breaks
  «Reproducible placement» and proposed constants of the engine version, before any code.
- The TDD sandbox could not be written from a Claude worktree session: the guard took the sandbox for
  the main checkout, and Claude Code forbids writing into another git worktree. Tests were written in a
  separate session. The `red` step wrote no auditor briefs when a changed non-test helper showed «NOT
  FOUND», and `close` did not copy helpers under `frontend/src/test/` (copied by hand in slice 3). The
  three defects were fixed on the branch `fix/sandbox-worktree-helpers`.
- A joined-chains test failed because of a frozen clock (both fills at one instant); the code was right,
  the test now advances the clock.
- The engine was created at import time as a default argument of `read_due_mailboxes`; the invariant
  review found it and it became lazy.
- The flow-checker was blocked by the auto-mode classifier on typing the test password, even after the
  user allowed it; the main session ran the manual checks itself. The flow-checker also clicked «Выйти»
  on an existing dev session and left the throwaway password on the Windows clipboard.

## What remains

- Task 1.4: manual placement and rules; «Заполнить» must keep manual placements; the thread-delete
  cascade and the merge rule for manual placements.
- Accepted spec gaps (behavior per design, no scenario): the order of counterparties, threads and
  chains; thread grouping beyond the pair case; «earlier» chain for a thread name means the first
  email's date; a chain in another project's «Неразобранное» counts as in that project; a placed chain
  stays when a later filled project fits better.
- Code issues not mitigated: a rare deadlock between a reading batch (locks chain rows, then project
  rows) and a fill (project rows, then placements); every fill and every batch with a filled project
  reads all the user's email texts for the IDF corpus (a tech-debt candidate if slow);
  `place_new_chains` takes project-row locks before checking that any project is filled.
- Left in the dev stack: the demo reply added by `add-new` stays in GreenMail (`just demo-mail`
  reloads it).
