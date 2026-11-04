# Spec Delta

## ADDED Requirements

### Requirement: FR-55 Edit a project

On the page of a project, «Изменить» SHALL let the user change its name and description by the checks
of creation; the same-name check SHALL ignore the project itself. Saving SHALL move no chain. A filled
project whose description changed after its last filling SHALL show «Описание изменено после
заполнения: нажмите «Заполнить», чтобы пересобрать проект» until it is filled again.

#### Scenario: Renaming a project
- **WHEN** Анна renames «Ремонт офиса» to «Ремонт офиса на Лесной», and her rule «Домен» «stroymaster.example» targets that project, thread «Смета»
- **THEN** «Проекты» lists «Ремонт офиса на Лесной», «Правила» lists «Домен: stroymaster.example → Ремонт офиса на Лесной → Смета», and the page of a chain in it shows «Ремонт офиса на Лесной»

#### Scenario: Changing only the letter case
- **WHEN** Анна renames her project «Ремонт офиса» to «ремонт офиса»
- **THEN** the project is saved as «ремонт офиса»

#### Scenario: A name of another project
- **WHEN** Анна has the projects «Ремонт офиса» and «Закупка техники» and renames «Закупка техники» to «РЕМОНТ ОФИСА»
- **THEN** nothing is saved and the form shows «Проект с таким названием уже есть»

#### Scenario: Empty or too long fields
- **WHEN** Анна saves the project with a name of only spaces, or a description of 2001 characters
- **THEN** nothing is saved and the form shows «Укажите название проекта» or «Описание — не длиннее 2000 символов»

#### Scenario: A changed description moves nothing
- **WHEN** «Ремонт офиса» is filled and Анна changes its description to «Ремонт офиса на Лесной: смета и акты»
- **THEN** every chain of the project stays in its place with its placement, similarity and engine version, and the page shows «Описание изменено после заполнения: нажмите «Заполнить», чтобы пересобрать проект»

#### Scenario: The hint goes after filling
- **WHEN** the page of «Ремонт офиса» shows the hint and Анна presses «Заполнить»
- **THEN** the project is filled again by the new description and the hint is no longer shown

#### Scenario: Only the name changed
- **WHEN** «Ремонт офиса» is filled and Анна changes only its name, or saves its description unchanged
- **THEN** the page shows no hint

#### Scenario: An unfilled project
- **WHEN** Анна changes the description of «Отпуск», which was never filled
- **THEN** the page shows no hint and still shows «Проект пуст: нажмите «Заполнить», чтобы найти его переписку»

#### Scenario: Another user's project
- **WHEN** Вера changes the name or description of a project of Анна by its identifier
- **THEN** the answer is «not found» and Анна's project does not change

### Requirement: FR-56 Delete a project

On the page of a project, «Удалить проект» SHALL ask «Удалить проект «<name>»? Цепочек в проекте: N —
они останутся в «Переписке» как убранные вручную. Правил, ведущих в проект: M — они будут удалены.
Письма не удаляются.» with «Удалить» and «Отмена». On «Удалить» the project, its threads and the rules
targeting it SHALL be deleted, every chain in it SHALL become taken out by hand with all its emails
kept, and the user SHALL land on «Проекты».

#### Scenario: Deleting a project
- **WHEN** «Ремонт офиса» holds 4 chains in threads and 1 in «Неразобранное», 2 rules target it, and Анна presses «Удалить проект»
- **THEN** she is asked «Удалить проект «Ремонт офиса»? Цепочек в проекте: 5 — они останутся в «Переписке» как убранные вручную. Правил, ведущих в проект: 2 — они будут удалены. Письма не удаляются.», and after «Удалить» she is on «Проекты», which no longer lists «Ремонт офиса», and «Правила» no longer lists those 2 rules

#### Scenario: The chains of a deleted project
- **WHEN** Анна has deleted «Ремонт офиса», which held «Смета на ремонт офиса» placed by the engine, «Акт скрытых работ» placed by hand and «Выбор дизайна переговорной» placed by a rule
- **THEN** each of them is listed in «Переписка» with all its emails, and its page shows «Вне проектов · убрана вручную»

#### Scenario: Deleting cancelled
- **WHEN** Анна presses «Удалить проект» at «Ремонт офиса» and presses «Отмена»
- **THEN** the project, its tree and its rules are as they were

#### Scenario: An empty project
- **WHEN** Анна deletes «Отпуск», which holds no chain and no rule targets
- **THEN** she is asked with «Цепочек в проекте: 0» and «Правил, ведущих в проект: 0», and after «Удалить» «Отпуск» is no longer listed

#### Scenario: The name is free again
- **WHEN** Анна has deleted «Ремонт офиса» and creates a project «Ремонт офиса»
- **THEN** the new project is created and is empty

#### Scenario: A deleted project
- **WHEN** Анна opens or deletes «Ремонт офиса» by its identifier after it was deleted
- **THEN** she sees «Страница не найдена» and the answer is «not found»

#### Scenario: Another user's project
- **WHEN** Вера deletes a project of Анна by its identifier
- **THEN** the answer is «not found», and Анна's project, its chains and its rules do not change
