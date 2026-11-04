# projects Specification

## Purpose
Lets a user create projects with a description, see the list of their projects and open a project as a
tree of its counterparties, threads and reply chains.

## Requirements

### Requirement: FR-32 Create a project

A user SHALL create a project by giving a name of 1 to 100 characters and a description of 1 to 2000
characters; leading and trailing spaces SHALL be dropped. One user SHALL NOT have two projects whose
names differ only in letter case. A new project SHALL be empty until it is filled.

#### Scenario: A new project
- **WHEN** Анна creates the project «Ремонт офиса» with the description «Ремонт офиса на Лесной: смета, график работ, акты, дизайн переговорной»
- **THEN** she lands on the page of «Ремонт офиса», which shows «Проект пуст: нажмите «Заполнить», чтобы найти его переписку»

#### Scenario: Empty or too long fields
- **WHEN** Анна submits the form with a name of only spaces, or a description of 2001 characters
- **THEN** nothing is saved and the form shows «Укажите название проекта» or «Описание — не длиннее 2000 символов»

#### Scenario: The same name twice
- **WHEN** Анна has the project «Ремонт офиса» and creates «ремонт офиса»
- **THEN** nothing is saved and the form shows «Проект с таким названием уже есть»

#### Scenario: Another user has the same name
- **WHEN** Вера creates «Ремонт офиса» while Анна has a project with that name
- **THEN** Вера's project is created and Анна's list does not change

### Requirement: FR-33 List the projects

«Проекты» SHALL list the user's projects by name in alphabetical order. Each project SHALL show its
name, the number of reply chains in its threads and the number in its «Неразобранное». A user without
projects SHALL see an invitation to create one.

#### Scenario: The list of projects
- **WHEN** Анна has the project «Конференция ТехФорум» with 3 chains in threads and «Ремонт офиса» with 3 chains in threads and 1 in «Неразобранное»
- **THEN** «Проекты» shows «Конференция ТехФорум» with «3 цепочки» first, then «Ремонт офиса» with «3 цепочки» and «1 неразобранная»

#### Scenario: No projects yet
- **WHEN** Вера has created no project
- **THEN** «Проекты» shows «Проектов пока нет: создайте первый» and the button «Создать проект»

#### Scenario: Only one's own projects
- **WHEN** Анна and Вера both have projects and Вера opens «Проекты»
- **THEN** she sees only her own projects

### Requirement: FR-34 Show a project as a tree

A project page SHALL show its name, description and tree: the counterparties of its chains by name, under
each the threads holding that counterparty's chains, under each thread those chains with their subject,
number of emails and latest date; then «Неразобранное» with its chains. A counterparty SHALL be one
participant address, named by the latest name it wrote with, else by the address.

#### Scenario: The tree of a project
- **WHEN** Анна opens «Ремонт офиса», whose thread «Смета на ремонт офиса» holds the chains «Смета на ремонт офиса» and «Акт скрытых работ» with «s.petrov@stroymaster.example», named «Сергей Петров» in his emails
- **THEN** she sees «Сергей Петров» with «s.petrov@stroymaster.example», under him the thread «Смета на ремонт офиса», under it both chains with their number of emails and latest date

#### Scenario: A chain with two counterparties
- **WHEN** a chain of «Ремонт офиса» has the participants «s.petrov@stroymaster.example» and «o.smirnova@interior-studio.example»
- **THEN** the chain is shown under both counterparties, in the same thread

#### Scenario: A chain without counterparties
- **WHEN** a chain of the project holds only emails between Анна's own addresses
- **THEN** it is shown under «Без контрагента»

#### Scenario: Opening a chain from the tree
- **WHEN** Анна clicks the chain «Акт скрытых работ» in the tree
- **THEN** she sees the chain with its emails, as in «Переписка»

#### Scenario: Another user's project
- **WHEN** Вера opens a project by the identifier of a project of Анна
- **THEN** she sees «Страница не найдена» and the answer to the request is «not found»

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
