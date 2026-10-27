# Spec Delta

## Purpose

Lets an administrator see who belongs to the organization, close access for an employee who left while
keeping their history, and share the administrator role.

## ADDED Requirements

### Requirement: FR-13 List the members of the organization

An administrator SHALL see the confirmed members of their organization, ordered by name. Each member
SHALL show the name, the email, the role («Администратор» or «Сотрудник») and the state («Активен» or
«Отключён»). The list SHALL hold only members of the administrator's own organization.

#### Scenario: The members list
- **WHEN** Анна, the administrator of «ООО Ромашка» with the employees Борис and Дина, opens «Участники»
- **THEN** she sees three rows: «Анна Петрова» «Администратор» «Активен», «Борис Иванов» «Сотрудник» «Активен», «Дина Орлова» «Сотрудник» «Активен»
- **AND** no member of the organization «Лютик» appears

### Requirement: FR-14 Deactivate and reactivate a member

An administrator SHALL deactivate another member of their organization. A deactivated member SHALL be
refused sign-in with «Учётная запись отключена. Обратитесь к администратору организации», and their
sessions SHALL end at once. Their data and history SHALL be kept. An administrator SHALL reactivate a
deactivated member, who can then sign in with their password. An administrator SHALL NOT deactivate
themselves.

#### Scenario: Deactivating an employee
- **WHEN** Анна deactivates Борис while he is signed in, and Борис then opens a page and later signs in with his password
- **THEN** his open page sends him to «Вход», sign-in shows «Учётная запись отключена. Обратитесь к администратору организации», and he stays in the list as «Отключён»

#### Scenario: Reactivating
- **WHEN** Анна reactivates Борис and he signs in with his old password
- **THEN** he is signed in as an employee

#### Scenario: Deactivating oneself
- **WHEN** Анна tries to deactivate herself
- **THEN** nothing changes and the page shows «Нельзя отключить свою учётную запись»

### Requirement: FR-15 Appoint and remove administrators

An administrator SHALL make an active employee of their organization an administrator, and SHALL make an
administrator an employee again. The new role SHALL apply to the member's next request without a new
sign-in.

#### Scenario: Appointing an administrator
- **WHEN** Анна makes Борис an administrator while he is signed in, and Борис opens «Участники»
- **THEN** Борис sees the members list and can invite employees

#### Scenario: Removing the role
- **WHEN** Борис, now an administrator, makes Анна an employee, and Анна then opens «Участники»
- **THEN** Анна sees «Страница не найдена» and the start page no longer offers «Участники»

### Requirement: FR-16 Keep at least one active administrator

An organization SHALL always keep at least one active administrator. Deactivating the last active
administrator or removing their role SHALL be refused with «В организации должен остаться хотя бы один
активный администратор». Two administrators acting at the same time SHALL NOT leave the organization
without one.

#### Scenario: The last administrator removes their own role
- **WHEN** Анна is the only active administrator and makes herself an employee
- **THEN** her role stays «Администратор» and the page shows «В организации должен остаться хотя бы один активный администратор»

#### Scenario: Two administrators remove each other at once
- **WHEN** Анна and Борис are the only administrators and at the same moment Анна makes Борис an employee and Борис makes Анна an employee
- **THEN** one change is applied, the other is refused with the same message, or with «Не найдено» when the applied change has already made its author an employee, and one active administrator remains
