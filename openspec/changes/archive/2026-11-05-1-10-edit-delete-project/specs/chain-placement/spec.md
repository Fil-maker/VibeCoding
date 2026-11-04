# Spec Delta

## MODIFIED Requirements

### Requirement: FR-41 Take a chain out of projects

On the page of a chain in a project, «Убрать из проекта» SHALL take the chain out of its project; the
page SHALL then show «Вне проектов · убрана вручную». The chains of a project the user deletes SHALL be
taken out the same way. Neither the engine, by «Заполнить» or after new emails, nor a rule SHALL ever
place such a chain again; only the user SHALL place it back by hand.

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

#### Scenario: The chains of a deleted project are not taken again
- **WHEN** Анна has deleted «Ремонт офиса», which held «Смета на ремонт офиса» from «s.petrov@stroymaster.example», then fills «Закупка техники» described as «Смета на ремонт офиса», a new email of that chain is read, and she creates the rule «Адрес отправителя» «s.petrov@stroymaster.example» → «Закупка техники»
- **THEN** «Смета на ремонт офиса» is still in no project and the rule's list of chains to move does not name it; Анна moves it by hand into «Закупка техники», where it shows «Вручную»
