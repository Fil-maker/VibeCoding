# Manual placement and re-sorting

Date: 02.11.2026 · Task: 1.4 · Change: 1-4-manual-placement

## Goal

Let the user correct the engine: move a chain by hand into a project, a thread or «Неразобранное», take it
out of projects for good, and re-sort a project explicitly while what was placed by hand stays. The plan
row is «Manual placement and re-sorting». Rules by address, domain or subject were split off into the new
task 1.5.

Before this task the user could not fix an engine mistake: a chain could not be moved or added, and a
repeated «Заполнить» deleted all threads of the project, including any hand placement in them.

## What was done

- Design session: the path was «new capability». The plan was split into 1.4 (by hand and re-sorting) and
  1.5 (rules). The change `1-4-manual-placement` got a proposal, a delta of `chain-placement`, a design and
  tasks. The delta adds FR-40 (place a chain by hand), FR-41 (take a chain out of projects) and FR-42
  (placements by hand are kept), and modifies FR-35, FR-36, FR-37 and FR-39. `openspec validate --strict`
  passed and the user approved the deltas.
- Branch: the workspace branch lacked the already merged task 1.3 (v0.2.0), so `feat/1-4-manual-placement`
  was created from the fresh `main`.
- Schema: migration `0006` makes `project_id`, `similarity` and `engine_version` of `chain_placements`
  nullable and adds checks on `kind` and shape. A placement now has the kind `engine`, `manual` or
  `excluded`; a chain taken out is a row of kind `excluded` without a project, so every existing query for
  chains without a placement skips it unchanged.
- Backend: routes `GET`/`PUT`/`DELETE /placements/{chain_id}` and `GET /projects/{id}/threads`; the module
  `hand_placing.py`; re-sorting keeps the threads that hold hand-placed chains with their ids, names and
  positions; on a merge of chains a hand placement wins over the engine's. Moving, taking out and re-sorting
  take the same per-user project lock as reading a mailbox. All queries filter by owner.
- SPA: the chain page `/chains/:id` got a block «Проект» with the form «Перенести» and the button «Убрать из
  проекта»; the project tree marks hand-placed chains with «Вручную»; the re-sorting confirmation starts with
  «Пересобрать проект?».
- Tests were written before the code from the scenarios, in the sandbox; auditors found weak and wrongly
  labelled tests, which the test-writer fixed. 35 new backend tests and 37 SPA tests.
- Manual flows in a browser passed: a move into a new thread «Акты»; re-sorting «Ремонт офиса» (the chain
  stayed in «Акты» marked «Вручную»); «Убрать из проекта» and a repeated «Заполнить» of «Закупки техники»
  (the chain did not return); a new email and a mailbox read moved nothing. The test account and the
  temporary sandbox database were deleted afterwards.
- Finish: `just check` 17/17 PASS; tests backend unit 90, frontend 141, database 223; `alembic check` shows no
  drift. The invariant review found no BLOCKER. Findings fixed by `code-writer`: the stale docstring of
  `list_placed_chain_ids_for_owner`, a duplicate `SIMILARITY_DECIMALS`, a missing thread in `_location` now
  raises NotFound, the «Ветка» select now starts at the chain's current thread (new test). The gap in
  `docs/architecture.md` was closed by `/document`; the finding on the fallback in `format.ts` was rejected because the
  database shape check guarantees an engine row has its version and similarity. The API client was regenerated after the docstring edits.
- Docs: the glossary term «Placement» in `docs/domain.md`; in `docs/ideas.md` the entry «Rules and manual
  placement» was replaced by «Edit threads by hand»; ADRs 0057 to 0062.

## Key questions to the AI

- Which path does task 1.4 take, and is it split? The user chose «Новая возможность (рекомендую)» and «1.4
  вручную + пересортировка, 1.5 правила (рекомендую)». The AI had found the task too large for two code
  sessions: three independent parts, each with its own API and UI.
- Where does the user move a chain, where to, what does «Убрать из проекта» mean, how does re-sorting work?
  Answers: «На странице цепочки (рекомендую)», «Ветка, «Неразобранное» или новая ветка (рекомендую)»,
  «Навсегда вне проектов (рекомендую)», ««Заполнить», ручное остаётся (рекомендую)».
- Write the two plan rows? «Да, записывай (рекомендую)».
- Approve the deltas? «Да, одобряю (рекомендую)».
- What should re-sorting do when the engine's chains had threads of their own before and a thread kept by
  hand is closest? The AI said the spec allows it (FR-36 «The engine adds to a kept thread») but it may
  surprise, and recommended leaving it and fixing through the idea «Edit threads by hand». The user
  answered «Да, как есть».
- Which decisions go to ADRs? The user chose «Без процессных (рекомендую)».

## Decisions

| Decision | Alternatives | Reason | Who |
| --- | --- | --- | --- |
| A chain is placed by hand on its own page /chains/:id: a block «Проект» shows where it is and a form «Перенести» | a menu in the project tree; both | На странице цепочки (рекомендую) | [human] |
| By hand a chain goes into any project of the user: an existing thread, «Неразобранное» or a new thread named by the user; renaming and merging threads are left for later | only an existing thread or «Неразобранное» | Ветка, «Неразобранное» или новая ветка (рекомендую) | [human] |
| «Убрать из проекта» keeps the chain out of every project for good: the engine never places it again by itself; only the user can place it back by hand | plain removal the engine may undo; no removal in 1.4 | Навсегда вне проектов (рекомендую) | [human] |
| The explicit re-sorting is «Заполнить» on a filled project: chains placed by hand and the threads holding them stay with their names, the engine lays out the rest again; the confirmation says so | a separate button «Пересортировать» | «Заполнить», ручное остаётся (рекомендую) | [human] |
| On a merge of chains a placement by hand wins over the engine's whatever its date; among placements of one kind the earliest wins | always the earliest placement | The PRD sets the priority: by hand, then a rule, then the engine | [AI → accepted] |
| Re-sorting keeps adding engine chains to the closest thread kept by hand, even when they had threads of their own before | keep the engine's earlier threads apart from the threads kept by hand | Да, как есть | [human] |

The path «new capability», the split into 1.4 and 1.5, plan 0.11 and the delta approval were also recorded
in the draft, but the user dropped them from the ADRs as process: they are visible in the plan and the
specs.

## Mistakes and lessons

- The workspace branch `claude/feature-1-4-6b413b` was behind `main`: task 1.3 was merged there as v0.2.0
  but absent in the branch. The state script therefore gave a stale next FR number; the AI noted FR-32 to
  FR-39 were already taken by 1.3 and expected FR-40. Later states showed «Next FR number: FR-43». Lesson:
  check that the branch contains the last merged task before trusting the state numbers.
- The «Ветка» select of the form «Перенести» started at «Неразобранное» instead of the chain's current
  thread. The AI listed it as a minor point in the handoff; the finish review made the select start at the
  current thread and added a test. A scenario for the form's initial value in the delta would have caught it
  before the code.
- The review at finish found a stale docstring, a duplicated constant `SIMILARITY_DECIMALS`, a silent miss of
  a thread in `_location` (now NotFound). Strict review of the diff
  against the rules caught them; the checks and tests did not.
- `docs/architecture.md` had no mention of the new kinds, routes and files until `/document` was run with
  the gap named by the review.
- Manual flows hit environment problems, not product ones: the frontend container could not download pnpm
  (Docker DNS failure), a local Vite took a wrong port (the backend checks Origin on 5173), then listened
  only on IPv6 while the preview browser used 127.0.0.1; the worktree had no `.env`, copied from the main
  checkout. Temporary entries in `.claude/launch.json` were reverted. Lesson: a documented way to start the
  SPA without Docker in a worktree would save the time.
- The surprising result of re-sorting (the engine puts «Смета» and «График» into the thread «Акты» kept by
  hand) was found only in the manual flow, not by the scenarios; it is accepted and noted in `docs/ideas.md`
  under «Edit threads by hand».

## What remains

- Task 1.5 «Rules»: rules by sender address, domain or subject that place new chains before the engine; what
  happens when two rules conflict and whether rules apply on «Заполнить» is left for its design.
- The idea «Edit threads by hand» in `docs/ideas.md`: renaming and merging threads, moving a chain right in
  the tree, batch moves; splitting a thread is the only way to undo the engine's adding to a thread kept by
  hand.
- The commit and merge of the change into `main` are done by `/finish` after this note.
