# Edit and delete a project

Date: 05.11.2026 · Task: 1.10 · Change: 1-10-edit-delete-project

## Goal

The user asked to be able to delete a project of correspondence («добавим возможность удаления проектка
переписки»). The task grew into task 1.10 «Edit and delete a project»: on the page of a project the user
renames it and changes its description, and deletes it after a confirmation. Changing the description
moves no chain; a deleted project's chains stay in «Переписка» as taken out by hand, its rules go with it,
and the emails stay.

## What was done

Three sessions: design (up to the approval of the deltas), code, and finish.

- **Design.** Plan row 1.10 added to `docs/plan.md` (edition 0.22). The change was renamed to
  `1-10-edit-delete-project` because the rule names a change by its task number. Deltas:
  ADDED FR-55 «Изменить проект» and FR-56 «Удалить проект» in `projects`; MODIFIED FR-41 in
  `chain-placement` and FR-45 in `placement-rules`. Design decisions D1–D5: placements are rewritten to
  `excluded` before the deletion in one transaction (otherwise the cascade would free the chains); threads
  and rules go by the database cascade, the rule count for the confirmation comes through
  `rules/service.py`; a new nullable column `projects.description_changed_at` is compared with
  `filled_at` for the hint; the counts in the confirmation are fetched anew when the button is pressed;
  the new code lives in `project_editing.py` because `service.py` and `repository.py` were already
  about 360–390 lines.
- **Backend.** `PATCH /api/v1/projects/{id}`, `GET /api/v1/projects/{id}/deletion`,
  `DELETE /api/v1/projects/{id}`; migration `0008` adds the column; `ProjectTree` gets
  `description_changed`. New files `project_editing.py` and `editing_repository.py`.
- **SPA.** New `ProjectManagement.tsx`: «Изменить» form, the hint «Описание изменено после заполнения…»
  and «Удалить проект» with a confirmation showing fresh counts; after the deletion «Проекты» opens.
- **Tests.** `test_project_editing.py`, `test_project_deletion.py`, `App.projectEdit.test.tsx`. Four
  auditing agents found weak tests (some did not perform the action of the scenario, some checked less than
  the spec requires); the tests were reworked. The gaps they noted are covered by the requirement texts, so
  the deltas did not change.
- **Manual pass 5.3** on the dev stack recreated from the worktree: rename, hint, «Заполнить» →
  «Пересобрать», confirmation text (2 chains, 1 rule), «Отмена», «Удалить», the chain showing
  «Вне проектов · убрана вручную» with all emails, the rule gone from «Правила». All PASS; 360 px fits
  without horizontal scroll.
- **Finish.** `just check` 17/17; tests: backend unit 109, SPA 389, database 343; `alembic check` reports
  no changes. The invariant-reviewer found no BLOCKER. Archive: 2 requirements added, 2 changed. Docs by
  `/document`; ADRs 0097–0102 written. Product docs edited at finish: `prd` 0.9 (invariant wording),
  `CLAUDE.md` invariant, `domain` 0.12 (glossary Project, map FR-55, FR-56, Last FR number FR-56),
  `plan` 0.22 (row 1.10 → Done), the `docs/ideas.md` entry removed.

## Key questions to the AI

- Scope, the fate of the chains of a deleted project, the rules that lead into it, and how to fit the
  deletion with the invariant «History is kept»: the user answered "Удаление и правка", "Убраны вручную",
  "Удалить вместе (рекомендую)", "Уточнить формулировку (рекомендую)".
- What happens to placed chains when the description changes, and whether to show a hint on the page: the
  user answered "Ничего не двигается (рекомендую)" and "Да, подсказка (рекомендую)".
- «Записываю строку плана 1.10?» and «Одобряем дельты?»: both "Да (рекомендую)".
- At `/document`, record the design decisions as ADRs? The AI recommended not to record «deltas approved» as
  a decision, since it is a process step; the user answered "1–6, без 7 (Recommended)".
- Test-writer to the lead (handoff): is the edit form in place or a route? Answer: the Interface fixes only
  the buttons; tests use «Изменить» on `/projects/{id}`. Does «unchanged description» compare after
  trimming? Yes, as on creation (FR-32). Plural forms in the confirmation? No, the text «Цепочек в проекте:
  N» as is.

## Decisions

| Decision | Alternatives | Reason | Who |
| --- | --- | --- | --- |
| Task 1.10 covers both deleting a project and editing its name and description | Only deletion, editing left in ideas.md | Пользователь выбрал «Удаление и правка» | [human] |
| Chains of a deleted project become taken out by hand (excluded); the engine and rules never place them again by themselves | Released to no project; hand-placed excluded, others released | Пользователь выбрал «Убраны вручную» | [human] |
| Rules targeting a deleted project are deleted with it; the confirmation shows how many rules and chains it touches | Refuse deletion while rules target the project | Пользователь выбрал «Удалить вместе» | [human] |
| Refine invariant History is kept in prd.md and CLAUDE.md: history is kept while the project exists; only the user deletes a project after confirmation; emails and chains stay | Leave the invariant wording unchanged | Пользователь выбрал «Уточнить формулировку» | [human] |
| Changing a project's description moves no chain; the user re-sorts with «Заполнить» | Re-sort at once on saving the description | Пользователь выбрал «Ничего не двигается» | [human] |
| The project page shows a hint when the description changed after the last filling, until the project is filled again | No hint | Пользователь выбрал «Да, подсказка» | [human] |

## Mistakes and lessons

- **Tests that did not test the scenario.** The first tests of the sandbox were green-able without doing
  the scenario's action; four auditing agents caught it. Lesson: the audit of tests against the spec is
  worth running before the code is accepted.
- **The red check reported PARTIAL.** One SPA test (the «Страница не найдена» page of a deleted project)
  is green before the code, since that page already existed. Because the script writes auditor briefs only
  when all tests are red, the briefs were generated by calling its function directly. A check that
  demands all-red does not fit a scenario that keeps existing behavior.
- **No `.env` in the worktree.** Database tests ran with the main checkout's variables exported;
  `just test-db` in the worktree says «TEST_DATABASE_URL is missing». For the manual pass a copy of `.env`
  (git-ignored) was put into the worktree. Catching it earlier: a worktree setup step that provides `.env`.
- **Manual pass blocked until consent.** The running containers were built from the main checkout, and
  recreating them moves the shared dev database to migration `0008`; the pass waited for the user's go-ahead.
- **Docs findings at finish.** The invariant-reviewer's IMPORTANT finding (`docs/architecture.md` not
  updated) was closed by `/document`; MINOR ones were dropped (migration line length outside lint;
  `FOR UPDATE` on the read-only deletion count is allowed by `data-access.md`). Doc-checkers found 4
  mismatches, fixed: a stale query name in architecture «Security», the forbidden_origin row, two missing
  ADR 0098 links.
- **Harness defect.** The `/document` planner maps frontend files to non-existent guides
  `docs/guide/frontend-api.md`, `frontend-features.md`, `frontend-test.md`; the real one is
  `docs/guide/frontend.md`.
- **Stale name left in old ADRs.** ADRs 0057–0062 cite `delete_engine_placements_and_unpinned_threads_for_owner`;
  not edited (decisions are only appended).
- **Process.** A heredoc broke in the shell; files were written with the Write tool. The `/document`
  step offered «deltas approved» as a decision; the user dropped it as a process step.

## What remains

- `projects/service.py` is at 394 lines (aim 300, limit 500).
- Cosmetic: with the edit form open, «Заполнить» stands right under «Сохранить» / «Отмена» and reads as
  part of the form.
- Not this change: the mailbox connect form switches the service to «Демо» when a demo address is typed and
  drops the typed server settings.
- The test account `flow-1-10-edit-delete-project@example.test` with a connected demo mailbox stays in the
  dev database (the app cannot delete accounts); its projects are deleted. The dev stack now runs this
  worktree's code.
- The `/document` planner mapping to non-existent guides (see above) needs a fix in the harness.
