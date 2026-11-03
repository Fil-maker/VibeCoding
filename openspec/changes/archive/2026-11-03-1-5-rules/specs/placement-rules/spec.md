## Purpose

Lets the user state once why correspondence belongs to a project — a sender address, a domain or words
of the subject — so that chains follow that reason before the engine compares them.

## ADDED Requirements

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
«Удалить» and «Отмена». Editing or deleting a rule SHALL NOT change any placement: the chains it placed
stay where they are.

#### Scenario: Editing a rule
- **WHEN** Анна changes the target of her rule «Домен» «techsnab.example» from «Закупка техники» to «Ремонт офиса» → «Поставки»
- **THEN** «Правила» lists «Домен: techsnab.example → Ремонт офиса → Поставки», and the chains the rule placed in «Закупка техники» stay there

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
