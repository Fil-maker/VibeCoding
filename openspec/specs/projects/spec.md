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
