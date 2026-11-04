# Spec Delta

## MODIFIED Requirements

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
