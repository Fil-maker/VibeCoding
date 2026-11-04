# Tasks

## 1. Scenario tests (test-writer, TDD sandbox)

- [x] 1.1 Backend integration tests for FR-55 (`test_project_editing.py`): rename, letter case only, a name of another project, empty and too long fields, a changed description moves nothing and sets `description_changed`, the hint goes after «Заполнить», a name-only or unchanged-description edit sets no hint, an unfilled project, another user's project — check — red against the current code.
- [x] 1.2 Backend integration tests for FR-56, FR-41 and FR-45 (`test_project_deletion.py`): the counts of `GET /deletion`, deletion with chains placed by the engine, by hand and by a rule becoming `excluded` and staying in «Переписка» with their emails, the rules targeting the project gone and others kept, an empty project, the name free again, a deleted project and another user's project answer 404 with nothing changed, the chains not taken again by «Заполнить», a new email or a rule, and placed back by hand — check — red against the current code.
- [x] 1.3 Test factories: `update_project`, `update_project_response`, `deletion_counts`, `delete_project`, `delete_project_response` in `backend/tests/factories.py`; the SPA harness answers for `PATCH`, `GET …/deletion` and `DELETE` in `frontend/src/test/projectTrees.tsx` — check — the tests of 1.1, 1.2 and 1.4 use them.
- [x] 1.4 SPA tests (`App.projectEdit.test.tsx`): the edit form with its messages and «Отмена», the hint shown and not shown, «Удалить проект» with the exact confirmation text and counts, «Удалить» landing on «Проекты», «Отмена» changing nothing — check — red against the current code.

## 2. Backend (code-writer)

- [x] 2.1 Migration `0008` adding `projects.description_changed_at`, nullable; downgrade drops it — check — `test_migrations.py` upgrade and downgrade pass.
- [x] 2.2 `project_editing.py` and its repository queries: edit with the FR-32 checks and the same-name check ignoring the project, set `description_changed_at` only on a changed description; the counts; deletion rewriting placements to `excluded` before deleting the project, in one transaction, under the owner filter — check — tests 1.1 and 1.2 pass.
- [x] 2.3 Router: `PATCH /{project_id}`, `GET /{project_id}/deletion`, `DELETE /{project_id}`; `ProjectTree.description_changed` — check — `just api-client` regenerates the client with no diff after a second run.

## 3. SPA (code-writer)

- [x] 3.1 `ProjectPage.tsx`: «Изменить» with the edit form, the hint, «Удалить проект» (danger kind) with the confirmation from fresh counts and the redirect to «Проекты» — check — tests 1.4 pass, every page reads at 360 px.

## 4. Docs

- [x] 4.1 Invariant «History is kept» refined in `docs/prd.md` (edition bump) and `CLAUDE.md`; `docs/domain.md` glossary «Project» and the requirements map (FR-55, FR-56), `Last FR number: 56`; the entry «Edit and delete a project» removed from `docs/ideas.md` — check — `just check` passes the doc links and facts.

## 5. Verification

- [x] 5.1 `just check` — check — passes with no warnings.
- [x] 5.2 `/test` all — check — unit and database tests pass.
- [x] 5.3 Manual flow by `flow-checker` on the demo mail: create and fill «Ремонт офиса», rename it, change its description and see the hint, fill and see it go, delete it with the confirmation, open a chain of it and see «Вне проектов · убрана вручную», see its rules gone from «Правила» — check — every step PASS.

## 6. Done when (plan task 1.10)

- [x] 6.1 On the page of a project «Изменить» changes its name and description by the checks of creation, and «Проекты», the rules and the chain pages show the new name.
- [x] 6.2 Changing the description moves no chain; a filled project then shows «Описание изменено после заполнения: нажмите «Заполнить», чтобы пересобрать проект» until it is filled again.
- [x] 6.3 «Удалить проект» asks for confirmation naming how many chains leave the project and how many rules are deleted; on «Удалить» the project is gone from «Проекты» and the user lands there, on «Отмена» nothing changes.
- [x] 6.4 After the deletion every chain of the project shows «Вне проектов · убрана вручную» and stays in «Переписка» with all its emails; neither «Заполнить» of another project, a rule nor a mailbox read places it again; only the user does by hand.
- [x] 6.5 The rules targeting the project are no longer listed on «Правила».
- [x] 6.6 A user editing or deleting another user's project gets «not found» and that project does not change.
- [x] 6.7 `just check` and `just test-all` pass.
