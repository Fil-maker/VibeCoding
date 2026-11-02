# chain-placement Specification

## Purpose
Places the user's reply chains into projects and threads — by the engine when a project is filled and
when new chains arrive — so that each placement says why it was made and the same emails always give
the same tree.

## Requirements

### Requirement: FR-35 Fill a project by the engine

«Заполнить» SHALL compare the description of the project with every reply chain of the user that is in
no other project. A chain whose similarity is at or above the sure threshold of the engine SHALL go to a
thread of the project, a chain between the lower and the sure threshold to «Неразобранное», a chain
below the lower threshold SHALL stay out. The engine SHALL group the project's chains into threads by
their similarity to each other.

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
переписку заново». On confirmation it SHALL drop the engine's placements of that project and fill it
again as an empty one; on cancel nothing SHALL change. Chains of other projects SHALL stay where they
are.

#### Scenario: Filling again
- **WHEN** Анна presses «Заполнить» on the filled «Ремонт офиса» and confirms
- **THEN** the project is filled again from its description and the chains of her other projects stay in place

#### Scenario: Cancelled
- **WHEN** Анна presses «Заполнить» on the filled «Ремонт офиса» and cancels
- **THEN** the tree of «Ремонт офиса» does not change

### Requirement: FR-37 Explain every placement

Every chain in a project's tree and in «Неразобранное» SHALL show how it got there: «Движок», the
engine version and the similarity of the chain to the project description in whole percent, as
computed when the chain was placed.

#### Scenario: A chain placed by the engine
- **WHEN** the engine «text-1» placed «Смета на ремонт офиса» in «Ремонт офиса» with the similarity 0.4271
- **THEN** the chain shows «Движок text-1 · сходство 43%»

#### Scenario: An unsure chain
- **WHEN** the engine «text-1» put a chain in «Неразобранное» with the similarity 0.1950
- **THEN** the chain shows «Движок text-1 · сходство 20%»

### Requirement: FR-38 Reproducible placement

The engine SHALL be deterministic: the same chains, the same project description and the same engine
version SHALL give the same threads with the same names, the same chains in each and the same
similarities, whatever the order the emails were read in. Each placement SHALL keep the version of the
engine that made it, so a placement by another version is visible.

#### Scenario: Filling twice gives the same tree
- **WHEN** Анна fills «Ремонт офиса», notes the tree, presses «Заполнить» again and confirms
- **THEN** the tree has the same threads, names, chains and similarities

#### Scenario: Another reading order
- **WHEN** Анна and Вера have the same emails, read in a different order, and each fills a project with the same description
- **THEN** both trees have the same threads, names, chains and similarities

#### Scenario: Another engine version
- **WHEN** the installation updates the engine from «text-1» to «text-2» and Анна does not fill «Ремонт офиса» again
- **THEN** its chains still show «Движок text-1», and after she fills it again they show «Движок text-2»

### Requirement: FR-39 Place new chains

After a mailbox read, an email that joins a placed chain SHALL leave the chain where it is. A chain in
no project that got new emails SHALL be compared with every filled project of the user: at or above the
sure threshold it SHALL go to the most similar project, into its closest thread or a new one; else
between the thresholds to that project's «Неразобранное»; else nowhere. The engine SHALL never move a
placed chain.

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
- **WHEN** a new email names emails of the chain «Смета на ремонт офиса», placed in «Ремонт офиса» first, and of a chain placed later in «Закупка техники»
- **THEN** the joined chain stays where «Смета на ремонт офиса» was, the placement made first

#### Scenario: Unfilled projects are skipped
- **WHEN** Анна has created «Отпуск» and not filled it, and a new chain about a vacation is read
- **THEN** the chain is not placed in «Отпуск»

#### Scenario: Only one's own projects
- **WHEN** a new chain is read from a mailbox of Вера and its text matches Анна's project «Ремонт офиса»
- **THEN** it is not placed in any project of Анна
