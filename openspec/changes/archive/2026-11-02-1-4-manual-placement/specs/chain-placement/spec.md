## ADDED Requirements

### Requirement: FR-40 Place a chain by hand

The page of a reply chain SHALL show where it is: its project and thread, its project's
«Неразобранное», or «Вне проектов». The user SHALL move the chain into any of their projects: into a
thread of that project, into its «Неразобранное» or into a new thread of that project with a name of 1
to 100 characters, spaces at the ends dropped. The chain's placement SHALL then be by hand. A thread
left without chains SHALL disappear.

#### Scenario: Moving a chain to another project
- **WHEN** the engine placed «Счёт на мониторы» in «Ремонт офиса» and Анна moves it on its page into the thread «Закупка мониторов» of «Закупка техники»
- **THEN** the chain is in that thread of «Закупка техники», no longer in «Ремонт офиса», and its page shows «Закупка техники → Закупка мониторов · Вручную»

#### Scenario: Placing a chain of no project
- **WHEN** «Выбор дизайна переговорной» is in no project and Анна moves it into «Неразобранное» of «Ремонт офиса»
- **THEN** the chain is in «Неразобранное» of «Ремонт офиса» and shows «Вручную»

#### Scenario: A new thread
- **WHEN** Анна moves «Акт скрытых работ» into a new thread «Акты» of «Ремонт офиса»
- **THEN** «Ремонт офиса» has the thread «Акты» holding that chain

#### Scenario: Pinning the engine's place
- **WHEN** the engine placed «Смета на ремонт офиса» in the thread «Смета на ремонт офиса» and Анна moves it into that same thread
- **THEN** the chain stays in that thread and shows «Вручную»

#### Scenario: A thread left empty
- **WHEN** the thread «Акты» holds only «Акт скрытых работ» and Анна moves that chain into «Неразобранное»
- **THEN** «Ремонт офиса» no longer has the thread «Акты»

#### Scenario: An empty or too long thread name
- **WHEN** Анна moves a chain into a new thread named only with spaces, or with 101 characters
- **THEN** nothing changes and the form shows «Укажите название ветки» or «Название ветки — не длиннее 100 символов»

#### Scenario: A thread of another project
- **WHEN** Анна sends a move into «Ремонт офиса» with the identifier of a thread of «Закупка техники»
- **THEN** the answer is «not found» and the chain stays where it was

#### Scenario: Another user's project or thread
- **WHEN** Вера moves her chain into a project or a thread of Анна by its identifier
- **THEN** the answer is «not found», Вера's chain stays where it was and Анна's project does not change

#### Scenario: Another user's chain
- **WHEN** Вера opens or moves a chain of Анна by its identifier
- **THEN** the answer is «not found» and the chain stays where it was

### Requirement: FR-41 Take a chain out of projects

On the page of a chain in a project, «Убрать из проекта» SHALL take the chain out of its project; the
page SHALL then show «Вне проектов · убрана вручную». The engine SHALL never place such a chain again,
neither by «Заполнить» nor after new emails; only the user SHALL place it back by hand.

#### Scenario: Taking a chain out
- **WHEN** «Скидка на абонемент в фитнес-клуб» is in «Неразобранное» of «Ремонт офиса» and Анна presses «Убрать из проекта»
- **THEN** the chain is in no project and its page shows «Вне проектов · убрана вручную»

#### Scenario: The engine does not take it back
- **WHEN** Анна has taken «Скидка на абонемент в фитнес-клуб» out, then fills «Ремонт офиса» again and a new email of that chain is read
- **THEN** the chain is still in no project

#### Scenario: Placing it back by hand
- **WHEN** Анна moves the taken-out chain into «Неразобранное» of «Ремонт офиса»
- **THEN** it is there and shows «Вручную»

#### Scenario: Taking out a chain in no project
- **WHEN** a request takes out a chain that is already out or in no project
- **THEN** nothing changes and the answer is «Цепочка не входит ни в один проект»

#### Scenario: Another user's chain
- **WHEN** Вера presses «Убрать из проекта» with the identifier of a chain of Анна
- **THEN** the answer is «not found» and Анна's chain stays where it was

### Requirement: FR-42 Placements by hand are kept

A chain placed by hand SHALL stay where the user put it: a new email in it, a mailbox read and
«Заполнить» SHALL NOT move it or take it out. When an email joins chains, the joined chain SHALL keep a
placement by hand over the engine's, whatever their dates; among placements of one kind it SHALL keep
the earliest.

#### Scenario: A new email in a chain placed by hand
- **WHEN** Анна moved «Акт скрытых работ» into the thread «Акты» and a reply in that chain is read
- **THEN** the chain stays in «Акты» and shows «Вручную»

#### Scenario: Joined with a chain of the engine
- **WHEN** the engine placed «Смета на ремонт офиса» in «Ремонт офиса» first, Анна later moved another chain into «Закупка техники» by hand, and a new email joins the two chains
- **THEN** the joined chain is in «Закупка техники» and shows «Вручную»

#### Scenario: Joined with a chain taken out
- **WHEN** Анна took a chain out of projects and a new email joins it with a chain the engine placed in «Ремонт офиса»
- **THEN** the joined chain is in no project and shows «Вне проектов · убрана вручную»

## MODIFIED Requirements

### Requirement: FR-35 Fill a project by the engine

«Заполнить» SHALL compare the description of the project with every reply chain of the user that is in
no project and was not taken out of projects by hand. A chain whose similarity is at or above the sure
threshold of the engine SHALL go to a thread of the project, a chain between the lower and the sure
threshold to «Неразобранное», a chain below the lower threshold SHALL stay out. The engine SHALL group
the project's chains into threads by their similarity to each other.

#### Scenario: Filling a project
- **WHEN** Анна, with the demo mail read, fills «Ремонт офиса» described as «Ремонт офиса на Лесной: смета, график работ, акты, дизайн переговорной»
- **THEN** the chains «Смета на ремонт офиса», «График работ и доступ в здание», «Акт скрытых работ» and «Выбор дизайна переговорной» are in the project, and none of the chains about laptops, monitors, servers or the conference

#### Scenario: Threads of a project
- **WHEN** the engine finds that the chains «Смета на ремонт офиса» and «Акт скрытых работ» are similar to each other and «Выбор дизайна переговорной» is not similar to either
- **THEN** the first two are in one thread named «Смета на ремонт офиса», the subject of the earlier one, and «Выбор дизайна переговорной» is in a thread of its own

#### Scenario: Unsure chains
- **WHEN** a chain's similarity to the description is between the lower and the sure threshold
- **THEN** the chain is in «Неразобранное» of the project and in no thread

#### Scenario: Chains of another project are not taken
- **WHEN** the chain «Счёт на мониторы» is in Анна's project «Закупка техники» and she fills a project «Мониторы» described as «Счёт на мониторы»
- **THEN** «Счёт на мониторы» stays in «Закупка техники»

#### Scenario: Chains taken out are not taken
- **WHEN** Анна took «Смета на ремонт офиса» out of projects and fills «Ремонт офиса»
- **THEN** «Смета на ремонт офиса» is in no project

#### Scenario: Nothing matches
- **WHEN** Анна fills a project described as «Аренда яхты на Байкале» and no chain reaches the lower threshold
- **THEN** the project stays empty and the page shows «Подходящей переписки не нашлось: уточните описание»

#### Scenario: Only one's own chains
- **WHEN** Вера fills her project «Ремонт офиса» while Анна has chains about the office renovation
- **THEN** no chain of Анна is in Вера's project, and Анна's projects do not change

#### Scenario: Another user's project
- **WHEN** Вера presses «Заполнить» with the identifier of a project of Анна
- **THEN** the answer is «not found» and Анна's project does not change

### Requirement: FR-36 Fill a filled project again

«Заполнить» on a project that already has chains SHALL ask «Пересобрать проект? Движок разложит его
переписку заново, а цепочки, размещённые вручную, останутся на месте». On confirmation it SHALL drop the
engine's placements of that project and the threads holding no chain placed by hand, keep the other
threads with their names, and fill the project again, into those threads or new ones; on cancel nothing
SHALL change. Chains of other projects SHALL stay where they are.

#### Scenario: Filling again
- **WHEN** Анна presses «Заполнить» on the filled «Ремонт офиса» and confirms
- **THEN** the project is filled again from its description and the chains of her other projects stay in place

#### Scenario: Cancelled
- **WHEN** Анна presses «Заполнить» on the filled «Ремонт офиса» and cancels
- **THEN** the tree of «Ремонт офиса» does not change

#### Scenario: Placements by hand survive filling again
- **WHEN** Анна moved «Акт скрытых работ» by hand into a new thread «Акты» of «Ремонт офиса», then fills the project again and confirms
- **THEN** «Акт скрытых работ» is still in «Акты» with «Вручную», and the thread keeps its name

#### Scenario: The engine adds to a kept thread
- **WHEN** the thread «Акты» of «Ремонт офиса» holds a chain placed by hand and, on filling again, the engine finds a sure chain closest to «Акты»
- **THEN** that chain is in «Акты» and shows «Движок» with its similarity

### Requirement: FR-37 Explain every placement

Every chain in a project's tree and in «Неразобранное» SHALL show how it got there: «Вручную» when the
user placed it by hand; else «Движок», the engine version and the similarity of the chain to the project
description in whole percent, as computed when the chain was placed.

#### Scenario: A chain placed by the engine
- **WHEN** the engine «text-1» placed «Смета на ремонт офиса» in «Ремонт офиса» with the similarity 0.4271
- **THEN** the chain shows «Движок text-1 · сходство 43%»

#### Scenario: An unsure chain
- **WHEN** the engine «text-1» put a chain in «Неразобранное» with the similarity 0.1950
- **THEN** the chain shows «Движок text-1 · сходство 20%»

#### Scenario: A chain placed by hand
- **WHEN** Анна moved «Акт скрытых работ» into the thread «Акты» by hand
- **THEN** the chain in the tree shows «Вручную» and no similarity

### Requirement: FR-39 Place new chains

After a mailbox read, an email that joins a placed chain SHALL leave the chain where it is. A chain in
no project that got new emails and was not taken out of projects by hand SHALL be compared with every
filled project of the user: at or above the sure threshold it SHALL go to the most similar project,
into its closest thread or a new one; else between the thresholds to that project's «Неразобранное»;
else nowhere. The engine SHALL never move a placed chain.

#### Scenario: A reply stays in its chain's place
- **WHEN** «Смета на ремонт офиса» is in the thread «Смета на ремонт офиса» and Сергей Петров's new reply in it is read
- **THEN** the chain stays in that thread with its placement unchanged, and the reply is in it

#### Scenario: A new chain finds its project
- **WHEN** a new email «Смета на покраску стен в офисе» from «s.petrov@stroymaster.example», naming no other email, is read
- **THEN** its chain is in «Ремонт офиса», in the thread «Смета на ремонт офиса», and shows «Движок» with its similarity

#### Scenario: An unsure new chain
- **WHEN** a new chain's best similarity to the filled projects is between the lower and the sure threshold
- **THEN** it is in «Неразобранное» of the most similar project

#### Scenario: A new chain of no project
- **WHEN** a new chain «Скидка на абонемент в фитнес-клуб» is below the lower threshold for every project
- **THEN** it is in no project and is listed only in «Переписка»

#### Scenario: Two placed chains are joined
- **WHEN** a new email names emails of the chain «Смета на ремонт офиса», placed by the engine in «Ремонт офиса» first, and of a chain placed by the engine later in «Закупка техники»
- **THEN** the joined chain stays where «Смета на ремонт офиса» was, the placement made first

#### Scenario: Unfilled projects are skipped
- **WHEN** Анна has created «Отпуск» and not filled it, and a new chain about a vacation is read
- **THEN** the chain is not placed in «Отпуск»

#### Scenario: Only one's own projects
- **WHEN** a new chain is read from a mailbox of Вера and its text matches Анна's project «Ремонт офиса»
- **THEN** it is not placed in any project of Анна
