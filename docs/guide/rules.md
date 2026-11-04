# Rules

Updated 05.11.2026

**Code:** `backend/app/modules/rules/` (`router.py`, `service.py`, `domain.py`, `schemas.py`, `repository.py`, `models.py`,
`errors.py`, `test_domain.py`), the migration `backend/migrations/versions/0007_placement_rules.py`, the integration tests
`backend/tests/integration/test_rules_crud.py`, `test_placement_by_rules.py` and `test_placement_rules_with_engine.py`, the helpers
`backend/tests/rule_support.py`, and the SPA page `frontend/src/features/projects/RulesPage.tsx` (route `/rules`). The placing of a chain
by a rule is in `backend/app/modules/projects/rule_placing.py`, described in [Projects](projects.md#placing-by-rules). Applying a saved
rule now (the list of its moves and the apply) is in `backend/app/modules/projects/rule_applying.py`, described in
[Projects](projects.md#applying-a-rule-now).

**Requirements:** [FR-43 … FR-45](../../openspec/specs/placement-rules/spec.md) (create a rule, list the rules, edit and delete a rule) and
[FR-46](../../openspec/specs/chain-placement/spec.md) (place chains by rules). The map is in [Requirements map](../domain.md#requirements-map).

**Design:** [Components and processes](../architecture.md#components-and-processes) (placing by rules), [Layers](../architecture.md#layers),
[Data model](../architecture.md#data-model) (`placement_rules`), [Routes and API](../architecture.md#routes-and-api).

**Decisions:** [ADR 0063](../adr/0063-task-1-5-rules-is-a.md) (rules are a new capability),
[ADR 0064](../adr/0064-when-several-rules-match-a-chain.md) (the more specific rule wins),
[ADR 0065](../adr/0065-rules-apply-on-fill-before-the.md) (rules apply on fill before the engine),
[ADR 0066](../adr/0066-a-rule-targets-a-project-and.md) (a rule targets a project and a thread by name),
[ADR 0067](../adr/0067-rule-crud-moves-out-of-the.md) (rule CRUD is its own module).

**Related:** [Projects](projects.md) (placing by rules, applying a rule now, filling, the tree), [Auth and accounts](auth.md#access-boundary) (the owner
boundary), [Backend](backend.md#modules-layout) (the module layout).

## A rule

A rule is a user's instruction: chains that match its condition go to a project and to a thread of that project. The row is
`PlacementRule` in `models.py`, table `placement_rules`; its columns are in [Data model](../architecture.md#data-model).

Saving a rule moves no chain at once by itself. On the page «Правила» the list of the chains the rule would move follows the save,
and «Применить» places them; «Не сейчас» leaves them where they are. The list and the apply are described in
[Applying a rule now](projects.md#applying-a-rule-now).

| Field | Meaning |
|---|---|
| `condition` | `address` (the sender's address), `domain` (the sender's domain) or `subject` (words of the subject) |
| `value` | the address or domain, or the subject words |
| `project_id` | the project a match goes to; it must be one of the user's projects |
| `thread_name` | the thread's name; empty means «Неразобранное» |

The request body `RuleInput` in `schemas.py` takes `condition`, `value`, `project_id` and `thread_name`. Creating and editing use the same
body, and an unknown field answers 422 `validation_failed`. The checks, from `schemas.py`:

- `address`: trimmed and lower-cased; it needs a local part, one `@`, a host, no spaces, and at most 254 characters. Otherwise
  «Укажите адрес почты».
- `domain`: trimmed and lower-cased; at least two labels of letters, digits or hyphens, and at most 253 characters. Otherwise
  «Укажите домен, например stroymaster.example».
- `subject`: runs of spaces become one space, the ends are trimmed, and the case is kept as the user wrote it. Empty answers
  «Укажите слова темы»; more than 200 characters answers «Слова темы — не длиннее 200 символов».
- `thread_name`: trimmed; an empty name is stored as no name (null). More than 100 characters answers
  «Название ветки — не длиннее 100 символов».
- `project_id`: missing or not an id answers «Выберите проект». A missing or non-text `value` gets the same message as an empty one.

The answer `Rule` carries `id`, `condition`, `value`, `project` (`id`, `name`) and `thread_name` (null for «Неразобранное»).

## Matching

`winning_rule` in `backend/app/modules/rules/domain.py` is the pure choice of the rule that places a chain. Its inputs are the
chain's senders (`ChainDocument.senders`: the distinct lower-cased `From` addresses of its emails) and its subject (the subject
of its first email). Recipients are never matched.

- **Address:** the rule's address equals one of the senders, lower-cased.
- **Domain:** a sender's host equals the domain or ends with a dot and the domain, so the sender «orders» at the host
  «sales.techsnab.example» matches the domain «techsnab.example», and the host «mytechsnab.example» does not.
- **Subject words:** the subject and the rule's value are read by `subject_words`: lower-cased, `ё` read as `е`, split on anything
  that is not a letter or a digit. Every word of the rule must be the start of some word of the subject (`word.startswith(part)`), so
  `акт` matches `Актуальные цены` and does not match `Новый контакт поставщика`. A value with no words never matches.

When several rules match, the order of `priority_key` decides: the address kind first, then the domain, then the subject words; among
one kind the earlier `created_at` wins, then the smaller `id`. `winning_rule` takes the first match in that order, whatever order it is
given in. The reason is [ADR 0064](../adr/0064-when-several-rules-match-a-chain.md). The repository lists the rules in the same order
(`_priority_order` in `repository.py`).

## Use cases

`RulesService` in `service.py` is bound to one session and has four use cases; every one runs in one transaction and filters by the
caller's `user_id`.

- **List** (`list_rules`): the user's rules in the order they win, at most `RULE_LIMIT` (200), with the names of their projects.
- **Create** (`create`): it locks the user's projects, then checks in this order: the target project is the user's (else `not_found`),
  the user has fewer than 200 rules (else `too_many_rules`), no rule has the same condition and a value equal ignoring case (else
  `rule_exists`). Then it inserts the row. A unique-index violation at flush (a race) also answers `rule_exists`.
- **Edit** (`update`): it reads the user's rule (else `not_found`), locks the user's projects, checks the target project (else
  `not_found`) and the repeat against the other rules (else `rule_exists`), then replaces every part of the rule. The limit does not apply
  to an edit.
- **Delete** (`delete`): it deletes the user's rule (else `not_found`). Placements the rule made keep their own copy of it
  ([Projects](projects.md#placing-by-rules)).

Deleting the rule's target project deletes the rule too: the foreign key `placement_rules.project_id` cascades. That deletion is
the projects module's ([Editing and deleting a project](projects.md#editing-and-deleting-a-project)), and the chains the project held
are taken out by hand, not moved by the rule ([ADR 0099](../adr/0099-rules-targeting-a-deleted-project-are.md)).

`count_rules_targeting` in `service.py` is a module function, not a `RulesService` use case. It returns how many of the user's rules
have the given `project_id`, through `count_rules_targeting_for_owner` in `repository.py`, in the caller's transaction. The deletion
confirmation of the projects module uses it as `rule_count`; the projects module reaches it only through this service.

No `RulesService` use case moves a placement; a rule's chains move only when the user applies the rule, which the projects module does
([Applying a rule now](projects.md#applying-a-rule-now)). `get_match_rule` in `service.py` is the one read of a single rule: it returns
the user's `MatchRule` for the id, or `None` for an unknown or another user's id, and the projects module uses it to read the rule it
lists or applies. It takes no lock and needs no use-case transaction of its own. The lock on the project rows keeps two parallel creates from both passing the 200-rule limit, as the
class docstring says. A repeat is refused by the unique index `uq_placement_rules_user_id_condition_lower_value` as well as by the check,
so a rule with the same value under another condition is not a repeat.

### The project directory

`ProjectDirectory` in `service.py` is a frozen dataclass of two callables. `names` takes the session, the user's id and a set of
project ids, and returns `id -> name` of those of the user's projects only; the list of rules passes the project ids of its rules. `lock_names`
takes the session and the user's id, locks all the user's projects and returns them as `id -> name`. `RulesService` gets the directory in its constructor, and
it never imports the projects module. The reason is the import cycle ([ADR 0067](../adr/0067-rule-crud-moves-out-of-the.md)): the projects
service imports the rules service (for `list_match_rules`, and `rule_placing.py` for `pick_winning_rule`), so the rules service cannot
import the projects service back.

`get_rules_service` in `router.py` builds the directory from `list_project_names` and `lock_project_names` of
`backend/app/modules/projects/service.py`. This is the only place in the rules module that imports the projects module.

## Routes

All routes need a signed-in caller (401 `not_signed_in` otherwise); the routes that change data also need the app's `Origin`.

| Method and path | Success | Errors |
|---|---|---|
| `GET /api/v1/rules` | 200, `list[Rule]`, in the order they win | none |
| `POST /api/v1/rules` | 201, `Rule` | `not_found` 404, `rule_exists` 409, `too_many_rules` 409, `validation_failed` 422 |
| `PUT /api/v1/rules/{rule_id}` | 200, `Rule` | `not_found` 404, `rule_exists` 409, `validation_failed` 422 |
| `DELETE /api/v1/rules/{rule_id}` | 204, no body | `not_found` 404 |

The router is tagged `rules` in the OpenAPI schema. The routes are listed with their schemas in [Routes and API](../architecture.md#routes-and-api).
Another user's rule or project answers `not_found`, the same as an unknown id.

## Errors over HTTP

| Code | Status | When | Message |
|---|---|---|---|
| `rule_exists` | 409 | the user already has a rule with this condition and a value equal ignoring case | «Такое правило уже есть» |
| `too_many_rules` | 409 | the user already has 200 rules | «Правил не может быть больше 200» |

`ERROR_MAPPING` in `router.py` holds the two codes. `main.py` imports it as `RULES_ERRORS` and registers it with the other modules'
mappings. The other codes are the shared ones of the platform ([Backend](backend.md)).

## The SPA

The page `/rules` (`RulesPage.tsx`, the title «Правила») has the form and the list of the user's rules in the order they win. The form has
the fields «Условие» (the conditions «Адрес отправителя», «Домен» and «Слова темы»), «Значение», «Проект» and «Ветка», and its button is
«Создать правило» for a new rule and «Сохранить» for an edit. Each rule has «Изменить» and «Удалить»; «Удалить» asks «Удалить правило?
Цепочки, уже размещённые им, останутся на месте» before it deletes. An empty list says «Правил пока нет»; with no project the page says
«Сначала создайте проект» with the link «Создать проект». After «Создать правило» or «Сохранить», the page shows the panel «Применить правило сейчас?» with the chains the rule would move
(`RuleApplyPanel.tsx`), and «Применить» or «Не сейчас»; the panel is described in [Applying a rule now](projects.md#applying-a-rule-now).
The header links to it as «Правила» ([Frames](frontend.md#frames)). The page's state handling is in [Frontend](frontend.md#rules-feature). A rule's explanation in the tree and on a chain page reads «Правило ·
адрес …», «Правило · домен …» or «Правило · слова темы «…»» (`format.ts`, see [Projects](projects.md#the-tree)).

## Modules and their files

| File | What it holds |
|---|---|
| `router.py` | `router` (`/api/v1/rules`), `ERROR_MAPPING` and `get_rules_service`, which builds the `ProjectDirectory`. A router holds no session. |
| `service.py` | `RulesService`, `ProjectDirectory`, and the functions the projects module uses: `list_match_rules` (the user's rules for matching), `get_match_rule` (one of the user's rules, or `None`), `count_rules_targeting` (how many rules lead into a project, for the deletion counts) and `pick_winning_rule`. It re-exports `MatchRule`. |
| `domain.py` | `RULE_LIMIT` (200), `MatchRule`, `priority_key`, `subject_words` and `winning_rule`. |
| `schemas.py` | `RuleCondition` (`address`, `domain`, `subject`), `RuleInput` with the checks, `RuleProject` and `Rule`. |
| `repository.py` | The owner-scoped queries: list (at most `RULE_LIMIT`), count, count of the rules targeting a project (`count_rules_targeting_for_owner`), get, the repeat check, add and delete. |
| `models.py` | `PlacementRule`, the table `placement_rules`. |
| `errors.py` | `RuleExists` and `TooManyRules`. |
| `test_domain.py` | The unit tests of the matching. |

`__init__.py` is empty. The module imports only its own files and the platform; the router's import of the projects service is the
one exception described above.

## Tests

- Unit: `backend/app/modules/rules/test_domain.py` covers the matching: no rule matches nothing; an address; a domain and its
  subdomains; the subject words, including a word inside another word; letter case and `ё`; an address over a domain and a domain over
  subject words; the earlier rule of one kind; senders compared ignoring case.
- Integration, through HTTP against the test database: `test_rules_crud.py` (create, the checks and the normalisation, the limit,
  a repeat, another user's project, list order, edit, delete, and the signed-in and Origin rules of the routes),
  `test_placement_by_rules.py` (placing by a rule alone, including the thread by name, the priority, and what a rule never takes),
  and `test_placement_rules_with_engine.py` (rules next to the engine, a fill, an edit or delete, the explanation kept, and the merge).
  The rules of a deleted target project are tested in `test_project_deletion.py` (FR-45, and the rule count of the deletion).
- Helpers: `backend/tests/rule_support.py` (`by_rule`, the rule shape of a placement; `anna_with_two_projects`), and
  `backend/tests/factories.py` (`create_rule` and `create_rule_response`, which post a rule).

`just test` runs the unit tests, `just test-db` the integration tests ([Integration tests](backend.md#integration-tests)).

## Changing it safely

- **A condition or the matching:** a behavior change goes through the spec first ([placement-rules spec](../../openspec/specs/placement-rules/spec.md),
  [chain-placement spec](../../openspec/specs/chain-placement/spec.md)), with the user's approval, then the code, the tests and this article.
- **The priority order:** it is the decision of [ADR 0064](../adr/0064-when-several-rules-match-a-chain.md). A change is a new decision.
- **The limit:** `RULE_LIMIT` is the only number; the message of `too_many_rules` is built from it. The create path must keep the project
  lock before the count, or two parallel creates can pass the limit.
- **A write that adds or retargets a rule** takes the project locks first, through `ProjectDirectory.lock_names`.
- **Imports:** the rules service never imports the projects module (the import cycle). The projects module reaches the rules only through
  `backend/app/modules/rules/service.py`.
- **A deleted target project** takes its rules with it through the cascade, so a rule never points at a missing project. The
  rule's chains are not moved to another project by that deletion ([Editing and deleting a project](projects.md#editing-and-deleting-a-project)).
- **Placements keep their copy of the rule.** An edit or a delete never rewrites a placement. A rule placement changes only on a fill of
  its project, which drops it and places again; by applying the rule now ([Applying a rule now](projects.md#applying-a-rule-now)); or by hand ([Projects](projects.md#placing-by-rules)).
