# placement-rules Specification

## Purpose
Lets the user state once why correspondence belongs to a project — a sender address, a domain or words
of the subject — so that chains follow that reason before the engine compares them.

## Requirements

### Requirement: FR-43 Create a rule

On the page «Правила» the user SHALL create a rule: a condition «Адрес отправителя», «Домен» or «Слова
темы» with its value, a target project of their own and an optional thread name of up to 100
characters; spaces at the ends SHALL be dropped and an empty thread name SHALL mean «Неразобранное».
An address or a domain SHALL be kept in lower case. A second rule with the same condition and value,
letter case ignored, SHALL be refused. A user SHALL have at most 200 rules.

#### Scenario: A rule by address
- **WHEN** Анна creates the rule «Адрес отправителя» «S.Petrov@StroyMaster.example» → «Ремонт офиса», thread «Смета»
- **THEN** «Правила» lists «Адрес отправителя: s.petrov@stroymaster.example → Ремонт офиса → Смета»

#### Scenario: A rule into «Неразобранное»
- **WHEN** Анна creates the rule «Домен» «techsnab.example» → «Закупка техники» with no thread name, or with a thread name of spaces only
- **THEN** «Правила» lists «Домен: techsnab.example → Закупка техники → Неразобранное»

#### Scenario: Invalid values
- **WHEN** Анна creates a rule by address with «petrov», by domain with «@techsnab» or «techsnab», by subject words with only spaces or with 201 characters, or with a thread name of 101 characters
- **THEN** no rule is created and the form shows «Укажите адрес почты», «Укажите домен, например stroymaster.example», «Укажите слова темы», «Слова темы — не длиннее 200 символов» or «Название ветки — не длиннее 100 символов»

#### Scenario: No project
- **WHEN** Анна creates a rule without choosing a project
- **THEN** no rule is created and the form shows «Выберите проект»

#### Scenario: A repeated rule
- **WHEN** Анна has the rule «Домен» «techsnab.example» and creates «Домен» «TechSnab.example» → «Ремонт офиса»
- **THEN** no rule is created and the form shows «Такое правило уже есть»

#### Scenario: Too many rules
- **WHEN** Анна has 200 rules and creates another
- **THEN** no rule is created and the page shows «Правил не может быть больше 200»

#### Scenario: Another user's project
- **WHEN** Вера creates a rule with the identifier of a project of Анна as its target
- **THEN** the answer is «not found» and no rule is created

### Requirement: FR-44 List the rules

The page «Правила» SHALL list the user's rules in the order they win: rules by address, then by domain,
then by subject words, each kind by the time of creation. Each rule SHALL show its condition, its value
and its target as «<project> → <thread>» or «<project> → Неразобранное». With no rules the page SHALL
show «Правил пока нет». A user SHALL see only their own rules.

#### Scenario: The order of rules
- **WHEN** Анна created the rules «Слова темы» «акт работ», then «Домен» «stroymaster.example», then «Адрес отправителя» «s.petrov@stroymaster.example»
- **THEN** «Правила» lists the address rule first, then the domain rule, then the subject words rule

#### Scenario: No rules
- **WHEN** Анна has no rules and opens «Правила»
- **THEN** she sees «Правил пока нет» and the form to create a rule

#### Scenario: Only one's own rules
- **WHEN** Анна has rules and Вера opens «Правила»
- **THEN** Вера sees none of Анна's rules

### Requirement: FR-45 Edit and delete a rule

The user SHALL change any part of their rule, by the same checks as on creation, and SHALL delete it
after the confirmation «Удалить правило? Цепочки, уже размещённые им, останутся на месте» with
«Удалить» and «Отмена». Editing a rule SHALL NOT move any chain by itself: chains move only when the user applies
the rule. Deleting a rule SHALL NOT change any placement: the chains it placed stay where they are. A
rule SHALL also be deleted when the user deletes its target project.

#### Scenario: Editing a rule
- **WHEN** Анна changes the target of her rule «Домен» «techsnab.example» from «Закупка техники» to «Ремонт офиса» → «Поставки»
- **THEN** «Правила» lists «Домен: techsnab.example → Ремонт офиса → Поставки», the page offers to apply the rule, and until «Применить» the chains the rule placed stay in «Закупка техники»

#### Scenario: An edit that repeats another rule
- **WHEN** Анна has the rules «Домен» «techsnab.example» and «Домен» «stroymaster.example» and changes the value of the second to «techsnab.example»
- **THEN** nothing changes and the form shows «Такое правило уже есть»

#### Scenario: Deleting a rule
- **WHEN** Анна presses «Удалить» at the rule «Адрес отправителя» «s.petrov@stroymaster.example» and confirms
- **THEN** the rule is no longer listed, and the chains it placed stay where they are

#### Scenario: Deleting cancelled
- **WHEN** Анна presses «Удалить» at a rule and presses «Отмена»
- **THEN** the rule is still listed

#### Scenario: Another user's rule
- **WHEN** Вера edits or deletes a rule of Анна by its identifier, or targets her own rule at a project of Анна
- **THEN** the answer is «not found» and the rules of both stay as they were

#### Scenario: The target project is deleted
- **WHEN** Анна has the rules «Домен» «stroymaster.example» → «Ремонт офиса» and «Домен» «techsnab.example» → «Закупка техники», and deletes «Ремонт офиса»
- **THEN** «Правила» lists only «Домен: techsnab.example → Закупка техники → Неразобранное», and a new chain from «stroymaster.example» goes by no rule

### Requirement: FR-47 Apply a rule now

After the user creates or edits a rule, «Правила» SHALL list the user's chains it would move — those
whose winning rule it is, in no project or placed by the engine or by a rule, and not already in its
project and thread — each with where it is and where it goes, and offer «Применить» and «Не сейчас»;
with none it SHALL show «Подходящих цепочек нет». «Применить» SHALL place by the rule the listed chains
that still qualify; «Не сейчас» SHALL move nothing. A thread left empty SHALL disappear.

#### Scenario: A chain in no project
- **WHEN** «Счёт на мониторы» from «i.volkov@techsnab.example» is in no project and Анна creates the rule «Домен» «techsnab.example» → «Закупка техники» with no thread name
- **THEN** the page lists «Счёт на мониторы: Вне проектов → Закупка техники → Неразобранное», and after «Применить» the chain is in «Неразобранное» of «Закупка техники» and shows «Правило · домен techsnab.example»

#### Scenario: A chain of the engine
- **WHEN** the engine placed «Счёт на мониторы» in the thread «Смета на ремонт офиса» of «Ремонт офиса» and Анна creates the rule «Слова темы» «мониторы» → «Закупка техники», thread «Мониторы», and presses «Применить»
- **THEN** «Закупка техники» has the thread «Мониторы» holding that chain, the chain shows «Правило · слова темы «мониторы»», and it is no longer in «Ремонт офиса»

#### Scenario: Not now
- **WHEN** the engine placed «Счёт на мониторы» in «Ремонт офиса», Анна creates the rule «Слова темы» «мониторы» → «Закупка техники» and presses «Не сейчас»
- **THEN** the chain stays in «Ремонт офиса» and shows «Движок»

#### Scenario: A chain placed by hand
- **WHEN** Анна moved «Акт скрытых работ» by hand into «Закупка техники» and creates the rule «Слова темы» «акт работ» → «Ремонт офиса»
- **THEN** the chain is not listed and stays in «Закупка техники» with «Вручную»

#### Scenario: A chain taken out
- **WHEN** Анна took «Акт сверки» out of projects and creates the rule «Слова темы» «акт» → «Ремонт офиса»
- **THEN** the chain is not listed and stays in no project

#### Scenario: A stronger rule wins
- **WHEN** the rule «Адрес отправителя» «i.volkov@techsnab.example» → «Ремонт офиса» placed «Счёт на мониторы», and Анна creates the rule «Домен» «techsnab.example» → «Закупка техники»
- **THEN** the chain is not listed and stays in «Ремонт офиса»

#### Scenario: A weaker rule's chain
- **WHEN** the rule «Домен» «techsnab.example» → «Ремонт офиса» placed «Счёт на мониторы» from «i.volkov@techsnab.example», and Анна creates the rule «Адрес отправителя» «i.volkov@techsnab.example» → «Закупка техники» and presses «Применить»
- **THEN** the page listed «Счёт на мониторы: Ремонт офиса → Неразобранное → Закупка техники → Неразобранное», and the chain is in «Неразобранное» of «Закупка техники» and shows «Правило · адрес i.volkov@techsnab.example»

#### Scenario: An edited target
- **WHEN** the rule «Домен» «techsnab.example» placed «Счёт на мониторы» and «Договор поставки» in «Закупка техники», Анна changes its target to «Ремонт офиса» → «Поставки» and presses «Применить»
- **THEN** both chains are in the thread «Поставки» of «Ремонт офиса» and show «Правило · домен techsnab.example»

#### Scenario: No longer matching after an edit
- **WHEN** the rule «Домен» «techsnab.example» placed «Счёт на мониторы» from «i.volkov@techsnab.example», and Анна changes the rule's value to «techsnab.ru» and presses «Применить»
- **THEN** the chain stays where it is and still shows «Правило · домен techsnab.example»

#### Scenario: Already in place
- **WHEN** the engine placed «Смета на ремонт офиса» in the thread «Смета на ремонт офиса» of «Ремонт офиса» and Анна creates the rule «Адрес отправителя» «s.petrov@stroymaster.example» → «Ремонт офиса», thread «смета на ремонт офиса»
- **THEN** the chain is not listed and keeps «Движок»

#### Scenario: Nothing to move
- **WHEN** Анна creates a rule that no chain of hers matches
- **THEN** the page shows «Подходящих цепочек нет» and no chain moves

#### Scenario: A thread left empty
- **WHEN** the thread «Мониторы» of «Ремонт офиса» holds only «Счёт на мониторы», placed by the engine, and Анна applies a rule that moves that chain to «Закупка техники»
- **THEN** «Ремонт офиса» no longer has the thread «Мониторы»

#### Scenario: Changed before «Применить»
- **WHEN** the page lists «Счёт на мониторы» and «Договор поставки», and before Анна presses «Применить» she moves «Договор поставки» by hand into «Ремонт офиса»
- **THEN** «Применить» moves «Счёт на мониторы» only, and «Договор поставки» stays in «Ремонт офиса» with «Вручную»

#### Scenario: Applied twice
- **WHEN** Анна presses «Применить» and then sends the same apply again
- **THEN** no chain moves the second time and the tree is the same

#### Scenario: Another user's rule or chains
- **WHEN** Вера asks for the list of, or applies, a rule of Анна by its identifier, or applies her own rule naming chains of Анна
- **THEN** the answer for Анна's rule is «not found», and no chain of Анна moves
