# Task 1.10 covers both deleting a project and editing its name and description

Id: 0097 · Date: 04.11.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: 1.10.
- Migration 0008 adds the nullable column projects.description_changed_at (timestamp); downgrade drops it. It is set only when an edit changes the trimmed description; ProjectTree.description_changed is true when the project was filled and description_changed_at is later than the last filling.
- New endpoints of the projects module: PATCH /api/v1/projects/{project_id} (body ProjectEdit: name, description; same checks as creation, the same-name check ignores the project itself; moves no chain), GET /api/v1/projects/{project_id}/deletion (ProjectDeletion: chain and rule counts for the confirmation), DELETE /api/v1/projects/{project_id} (204). Another user's or an unknown project answers 404. The global OriginGuardMiddleware guards PATCH and DELETE.
- backend/app/modules/projects/project_editing.py holds the edit, the deletion counts and the deletion use cases; backend/app/modules/projects/editing_repository.py holds their queries, every one filtered by user_id: lock the project, the name clash, the chain count, the placement rewrite.
- Deleting a project rewrites every chain_placements row of the project to kind excluded (taken out by hand) with the shape fields nulled and placed_at from the injected Clock, before deleting the project in the same transaction; its threads go with it and the rules targeting it go through the cascade on placement_rules.project_id. Emails and chains are not touched.
- The rules module gains count_rules_targeting_for_owner in rules/repository.py and count_rules_targeting in rules/service.py; the projects module counts rules only through the rules service.
- frontend/src/features/projects/ProjectManagement.tsx holds the project page's «Изменить» edit form, the hint «Описание изменено после заполнения: нажмите «Заполнить», чтобы пересобрать проект» and «Удалить проект» (danger kind) with a confirmation built from fresh counts of GET …/deletion; «Удалить» lands on «Проекты». It invalidates the projects, rules and reply-chain queries.
- The SPA test harness frontend/src/test/projectTrees.tsx answers PATCH /projects/{id}, GET /projects/{id}/deletion and DELETE /projects/{id}; backend/tests/factories.py gains update_project, update_project_response, deletion_counts, delete_project, delete_project_response.

## Decision
Task 1.10 covers both deleting a project and editing its name and description

## Alternatives
Only deletion, editing left in ideas.md

## Reason
Пользователь выбрал «Удаление и правка»
