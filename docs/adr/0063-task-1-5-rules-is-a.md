# Task 1.5 Rules is a new capability: a new spec rules plus MODIFIED requirements of chain-placement

Id: 0063 · Date: 02.11.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: 1.5.
- Task 1.5 adds the module backend/app/modules/rules/ (domain.py with RULE_LIMIT = 200, MatchRule and winning_rule; errors.py RuleExists, TooManyRules; models.py PlacementRule; repository.py; router.py; schemas.py with RuleCondition address|domain|subject, RuleInput, Rule; service.py RulesService) with rule CRUD; its router imports list_project_names and lock_project_names from projects.service, and projects.schemas imports RuleCondition from rules.schemas.
- Routes of the rules module: GET /api/v1/rules (the user's rules in priority order), POST /api/v1/rules, PUT /api/v1/rules/{rule_id}, DELETE /api/v1/rules/{rule_id}; OpenAPI tag rules; errors rule_exists («Такое правило уже есть») and too_many_rules («Правил не может быть больше 200»); another user's rule or project answers not found.
- To avoid a circular import, rules/service.py defines the frozen dataclass ProjectDirectory(names, lock_names): names(session, user_id, project_ids) gives the names of those projects, lock_names(session, user_id) locks all the user's projects and gives their names; rules/router.py builds it in get_rules_service from list_project_names and lock_project_names of projects/service.py. projects reaches rules only through rules.service (list_match_rules, pick_winning_rule, MatchRule).
- RulesService.create and update lock the user's projects (lock_projects_for_owner, with_for_update) before counting rules or checking the target project, so parallel creates cannot pass the 200-rule limit; a repeated rule is caught also by the unique index on (user_id, condition, lower(value)).
- Migration 0007_placement_rules: table placement_rules (id, user_id, condition, value, project_id, thread_name, created_at, updated_at; check condition; index ix_placement_rules_user_id; unique index on user, condition and lower(value)); chain_placements gains rule_condition and rule_value, a placement kind rule, and widened kind and shape checks; downgrade deletes rule rows.
- projects/rule_placing.py places a chain by the winning rule: into the project's first thread by position whose trimmed lower-cased name equals the rule's thread name (find_thread_by_name_for_owner), creating the thread when none exists, or into «Неразобранное» when the rule has no thread name; the placement row stores its own copy of the rule (add_rule_placement_for_owner with NewRulePlacement).
- Placement order: on a mailbox read new chains are placed by rules before the engine; «Заполнить» drops the project's engine and rule placements, places by rules first, gives the rest to the engine; placements by hand and taken-out chains are never moved; on merging chains hand beats rule beats engine.
- Matching: address equals a sender address of the chain in lower case; domain matches the sender domain or its subdomains; subject words match when each rule word begins a word of the subject, case ignored and «ё» read as «е»; an address wins over a domain, a domain over subject words, then the earlier created rule. ChainDocument.senders in correspondence gives the chain's distinct lower-cased sender addresses.
- SPA: page /rules (frontend/src/features/projects/RulesPage.tsx) with a form, the list, «Изменить», «Удалить» with confirmation, «Правил пока нет», «Сначала создайте проект»; link «Правила» on the start page; format.ts shows the rule explanations «Правило · адрес …», «Правило · домен …», «Правило · слова темы «…»» in the project tree and on the chain page.

## Decision
Task 1.5 Rules is a new capability: a new spec rules plus MODIFIED requirements of chain-placement

## Alternatives
changed behavior only inside chain-placement

## Reason
Новая возможность (рекомендую)
