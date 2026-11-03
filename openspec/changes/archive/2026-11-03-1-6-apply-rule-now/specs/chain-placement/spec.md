# Spec Delta

## MODIFIED Requirements

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
- **WHEN** the engine placed «Счёт на мониторы» in «Ремонт офиса», and Анна creates the rule «Слова темы» «мониторы» → «Закупка техники» and does not apply it
- **THEN** «Счёт на мониторы» stays in «Ремонт офиса» and shows «Движок»

#### Scenario: Only one's own chains
- **WHEN** Анна has the rule «Домен» «stroymaster.example» → «Ремонт офиса» and a new chain from Сергей Петров is read from a mailbox of Вера
- **THEN** the chain is in no project of Анна
