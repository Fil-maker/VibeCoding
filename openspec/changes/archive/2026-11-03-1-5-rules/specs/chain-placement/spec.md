## ADDED Requirements

### Requirement: FR-46 Place chains by rules

A rule SHALL match its user's chain when an email of it came from the rule's address, domain or
subdomain, or when each rule word begins a word of the first email's subject,
case ignored, «ё» as «е». An address SHALL win over a domain, a domain over subject words, then the
earlier rule. The chain SHALL go into the rule's project: its first thread named as the rule says, case
ignored, created if missing, or «Неразобранное». A chain placed by hand or taken out SHALL NOT be
placed by a rule.

#### Scenario: A rule by address
- **WHEN** Анна has the rule «Адрес отправителя» «s.petrov@stroymaster.example» → «Ремонт офиса», thread «Смета», «Ремонт офиса» has no thread «Смета», and a new chain «Смета на покраску стен» from Сергей Петров is read
- **THEN** «Ремонт офиса» has the thread «Смета» holding that chain, and the chain shows «Правило»

#### Scenario: A rule by domain
- **WHEN** Анна has the rule «Домен» «techsnab.example» → «Закупка техники» with no thread, and new chains from «i.volkov@techsnab.example», «orders@sales.techsnab.example» and «info@mytechsnab.example» are read
- **THEN** the first two are in «Неразобранное» of «Закупка техники» and show «Правило», and the third is not placed by that rule

#### Scenario: A rule by subject words
- **WHEN** Анна has the rule «Слова темы» «акт работ» → «Ремонт офиса», thread «Акты», and new chains «Акт скрытых работ» and «Акт сверки» are read
- **THEN** «Акт скрытых работ» is in the thread «Акты» and shows «Правило», and «Акт сверки» is not placed by that rule

#### Scenario: A word inside another word
- **WHEN** Анна has the rule «Слова темы» «акт» and a new chain «Новый контакт поставщика» is read
- **THEN** the chain is not placed by that rule

#### Scenario: Letter case and «ё»
- **WHEN** Анна has the rule «Слова темы» «счёт мониторы» and a new chain «СЧЕТ на мониторы» is read
- **THEN** the chain is placed by that rule

#### Scenario: An existing thread of that name
- **WHEN** «Ремонт офиса» has the thread «Смета на ремонт офиса» and a new chain matches a rule → «Ремонт офиса», thread «смета на ремонт офиса»
- **THEN** the chain is in the existing thread «Смета на ремонт офиса» and no new thread appears

#### Scenario: An address wins over a domain
- **WHEN** Анна has the rules «Домен» «stroymaster.example» → «Ремонт офиса» and, created later, «Адрес отправителя» «s.petrov@stroymaster.example» → «Закупка техники», and a new chain from Сергей Петров is read
- **THEN** the chain is in «Закупка техники»

#### Scenario: Of one kind the earlier wins
- **WHEN** Анна created the rule «Слова темы» «смета» → «Ремонт офиса», then «Слова темы» «офис» → «Закупка техники», and a new chain «Смета на ремонт офиса» is read
- **THEN** the chain is in «Ремонт офиса»

#### Scenario: A chain placed by hand
- **WHEN** Анна moved «Акт скрытых работ» by hand into «Закупка техники», then creates a rule «Слова темы» «акт работ» → «Ремонт офиса», and a reply in that chain is read
- **THEN** the chain stays in «Закупка техники» and shows «Вручную»

#### Scenario: A chain taken out
- **WHEN** Анна took «Акт сверки» out of projects, has a rule «Слова темы» «акт» → «Ремонт офиса», and a new email of that chain is read
- **THEN** the chain is still in no project

#### Scenario: A new rule moves nothing
- **WHEN** the engine placed «Счёт на мониторы» in «Ремонт офиса» and Анна creates the rule «Слова темы» «мониторы» → «Закупка техники»
- **THEN** «Счёт на мониторы» stays in «Ремонт офиса» and shows «Движок»

#### Scenario: Only one's own chains
- **WHEN** Анна has the rule «Домен» «stroymaster.example» → «Ремонт офиса» and a new chain from Сергей Петров is read from a mailbox of Вера
- **THEN** the chain is in no project of Анна

## MODIFIED Requirements

### Requirement: FR-35 Fill a project by the engine

«Заполнить» SHALL take every reply chain of the user that is in no project and was not taken out of
projects by hand. A chain whose winning rule targets this project SHALL be placed by that rule, a chain
whose winning rule targets another project SHALL stay out. The rest SHALL be compared with the
description: at or above the sure threshold of the engine a chain SHALL go to a thread of the project,
between the lower and the sure threshold to «Неразобранное», below the lower threshold it SHALL stay
out. The engine SHALL group the project's chains into threads by their similarity to each other.

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

#### Scenario: A rule of this project goes first
- **WHEN** «Выбор дизайна переговорной» is in no project, Анна has the rule «Адрес отправителя» of Ольга Смирнова → «Ремонт офиса», thread «Дизайн», and fills «Ремонт офиса»
- **THEN** the chain is in the thread «Дизайн» and shows «Правило», not «Движок»

#### Scenario: A rule of another project keeps a chain out
- **WHEN** Анна has the rule «Слова темы» «акт работ» → «Закупка техники» and fills «Ремонт офиса» while «Акт скрытых работ» is in no project
- **THEN** «Акт скрытых работ» is not in «Ремонт офиса»

### Requirement: FR-36 Fill a filled project again

«Заполнить» on a project that already has chains SHALL ask «Пересобрать проект? Движок разложит его
переписку заново, а цепочки, размещённые вручную, останутся на месте». On confirmation it SHALL drop the
placements of that project by the engine and by rules and the threads holding no chain placed by hand,
keep the other threads with their names, and fill the project again, into those threads or new ones;
on cancel nothing SHALL change. Chains of other projects SHALL stay where they are.

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

#### Scenario: An edited rule takes effect on filling again
- **WHEN** the rule «Слова темы» «акт работ» placed «Акт скрытых работ» in the thread «Акты» of «Ремонт офиса», Анна changes the rule's thread name to «Документы», then fills «Ремонт офиса» again and confirms
- **THEN** the chain is in the thread «Документы» and shows «Правило», and the thread «Акты» is gone

#### Scenario: A deleted rule on filling again
- **WHEN** a rule placed «Акт скрытых работ» in «Ремонт офиса», Анна deletes the rule, then fills «Ремонт офиса» again and confirms
- **THEN** the engine places the chain by its similarity, as any other chain in no project

### Requirement: FR-37 Explain every placement

Every chain in a project's tree, in «Неразобранное» and on its own page SHALL show how it got there:
«Вручную» when the user placed it by hand; «Правило» and the rule's condition and value as they were when
it placed the chain; else «Движок», the engine version and the similarity of the chain to the project
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

#### Scenario: A chain placed by a rule
- **WHEN** the rules «Адрес отправителя» «s.petrov@stroymaster.example», «Домен» «techsnab.example» and «Слова темы» «акт работ» each placed a chain
- **THEN** the chains show «Правило · адрес s.petrov@stroymaster.example», «Правило · домен techsnab.example» and «Правило · слова темы «акт работ»», in the tree and on their pages, with no similarity

#### Scenario: The rule changed after placing
- **WHEN** the rule «Домен» «techsnab.example» placed a chain and Анна then changes the rule's value to «techsnab.ru» or deletes the rule
- **THEN** the chain still shows «Правило · домен techsnab.example»

### Requirement: FR-39 Place new chains

After a mailbox read, an email that joins a placed chain SHALL leave the chain where it is. A chain in
no project that got new emails and was not taken out of projects by hand SHALL first go by its winning
rule, into any project of the user, filled or not. Else it SHALL be compared with every filled project:
at or above the sure threshold it SHALL go to the most similar project, into its closest thread or a new
one; else between the thresholds to that project's «Неразобранное»; else nowhere. The engine SHALL never
move a placed chain.

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

#### Scenario: A rule goes before the engine
- **WHEN** a new chain «Смета на покраску стен в офисе» from «s.petrov@stroymaster.example» would be sure for «Ремонт офиса», and Анна has the rule «Адрес отправителя» «s.petrov@stroymaster.example» → «Закупка техники»
- **THEN** the chain is in «Закупка техники» and shows «Правило»

#### Scenario: A rule into an unfilled project
- **WHEN** Анна has created «Отпуск» and not filled it, has the rule «Слова темы» «отпуск» → «Отпуск», and a new chain «Отпуск в июле» is read
- **THEN** the chain is in «Неразобранное» of «Отпуск» and shows «Правило»

### Requirement: FR-42 Placements by hand are kept

A chain placed by hand SHALL stay where the user put it: a new email in it, a mailbox read and
«Заполнить» SHALL NOT move it or take it out. When an email joins chains, the joined chain SHALL keep a
placement by hand over a rule's and a rule's over the engine's, whatever their dates; among placements of
one kind it SHALL keep the earliest.

#### Scenario: A new email in a chain placed by hand
- **WHEN** Анна moved «Акт скрытых работ» into the thread «Акты» and a reply in that chain is read
- **THEN** the chain stays in «Акты» and shows «Вручную»

#### Scenario: Joined with a chain of the engine
- **WHEN** the engine placed «Смета на ремонт офиса» in «Ремонт офиса» first, Анна later moved another chain into «Закупка техники» by hand, and a new email joins the two chains
- **THEN** the joined chain is in «Закупка техники» and shows «Вручную»

#### Scenario: Joined with a chain taken out
- **WHEN** Анна took a chain out of projects and a new email joins it with a chain the engine placed in «Ремонт офиса»
- **THEN** the joined chain is in no project and shows «Вне проектов · убрана вручную»

#### Scenario: A rule's placement over the engine's
- **WHEN** the engine placed «Смета на ремонт офиса» in «Ремонт офиса» first, a rule later placed another chain in «Закупка техники», and a new email joins the two chains
- **THEN** the joined chain is in «Закупка техники» and shows «Правило»

#### Scenario: A placement by hand over a rule's
- **WHEN** a rule placed a chain in «Ремонт офиса» first, Анна later moved another chain into «Закупка техники» by hand, and a new email joins the two chains
- **THEN** the joined chain is in «Закупка техники» and shows «Вручную»
