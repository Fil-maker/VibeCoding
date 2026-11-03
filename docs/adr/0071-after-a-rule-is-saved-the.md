# After a rule is saved the page lists the chains it would move (from → to) with «Применить» and «Не сейчас»; nothing moves without confirmation

Id: 0071 · Date: 03.11.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: 1.6.
- New routes: GET /api/v1/placements/by-rule/{rule_id} returns RuleMoves (the chains the rule would move, newest by latest email then chain id); POST /api/v1/placements/by-rule/{rule_id} with RuleApply {chain_ids, at most 5000} returns RuleApplied {moved}. Unknown or another user's rule → 404; unknown ids and chains that no longer qualify are skipped silently.
- New module backend/app/modules/projects/rule_applying.py: list_moves (read only) and apply_moves (runs after lock_projects_for_owner, recomputes the moves, intersects with the sent ids, deletes each former placement, places by rule_placing.place_by_rules with only this rule, deletes a former thread left empty via delete_thread_if_empty_for_owner).
- A rule moves a chain only when it is that chain's winning rule (rules.service.pick_winning_rule, FR-46 priority) and the chain is in no project or placed by the engine or by a rule (_MOVABLE_KINDS = ENGINE, RULE); chains placed by hand or taken out are never listed or moved; a chain already in the rule's project and thread is not listed.
- Schemas in projects/schemas.py: RuleMoveSource {state none|placed, project, thread}, RuleMoveTarget {project, thread_name; null = «Неразобранное»}, RuleMove {chain_id, subject, latest_email_at, current, target}, RuleMoves {moves}, RuleApply {chain_ids}, RuleApplied {moved}.
- ProjectsService.list_rule_moves and apply_rule; rules.service.get_match_rule(session, user_id, rule_id) returns the user's MatchRule or None.
- New repository functions in projects/repository.py: list_placements_for_owner, delete_placement_for_owner.
- SPA: frontend/src/features/projects/RuleApplyPanel.tsx shows after «Создать правило» and «Сохранить» on «Правила» the panel «Применить правило сейчас?» listing «<тема>: <откуда> → <проект> → <ветка или Неразобранное>» («Вне проектов» for no project), buttons «Применить» and «Не сейчас», buttons disabled while a request runs; after «Применить» «Перемещено цепочек: N» and «Понятно»; with no moves «Подходящих цепочек нет» and «Понятно». Texts are constants in the component.
- SPA test fixtures frontend/src/test/ruleMoves.tsx (RuleMove/RuleMoves/RuleApplied JSON and panel lookups); tests in frontend/src/App.ruleMoves.test.tsx; rulesPage.tsx fixture extended.
- Backend tests of the change: backend/tests/integration/test_placement_apply_rule.py, test_placement_apply_rule_edits.py, test_placement_apply_rule_requests.py; shared helpers in backend/tests/rule_support.py.

## Decision
After a rule is saved the page lists the chains it would move (from → to) with «Применить» and «Не сейчас»; nothing moves without confirmation

## Alternatives
Apply silently on save; a separate «Применить» button per rule

## Reason
Список и подтверждение (рекомендую)
