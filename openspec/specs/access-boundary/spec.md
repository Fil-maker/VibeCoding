# access-boundary Specification

## Purpose
Keeps every user inside their own organization and their own role: a signed-out visitor reaches
nothing protected, one organization never sees another, and an employee never reaches the
administrator's actions.

## Requirements

### Requirement: FR-17 Protected pages and actions need a signed-in user

Every page and action other than registration, confirmation, sign-in, password reset and invitation
acceptance SHALL require a signed-in, active user. A request without a valid session SHALL be refused
as signed out. The SPA SHALL send such a visitor to «Вход» and return them to the requested page after
sign-in.

#### Scenario: A signed-out visitor opens a protected page
- **WHEN** a visitor who is not signed in opens «Участники»
- **THEN** they see «Вход», and after Анна signs in there she lands on «Участники»

#### Scenario: A forged or ended session
- **WHEN** a request carries a session token that never existed or belongs to a session ended by sign-out
- **THEN** it is refused as signed out and no data is returned

### Requirement: FR-18 Organizations never see each other

Every page and action SHALL work only with the data of the signed-in user's organization. The
organization SHALL be taken from the session, never from the request. Members and invitations of
another organization SHALL answer «not found», the same answer as for data that does not exist.

#### Scenario: An administrator reaches into another organization
- **WHEN** Вера, the administrator of «Лютик», tries to deactivate Борис of «ООО Ромашка», or to revoke or resend an invitation of «ООО Ромашка», by its identifier
- **THEN** each request answers «not found» and nothing changes in «ООО Ромашка»

#### Scenario: An organization named in the request is ignored
- **WHEN** Вера sends an invitation request that names the organization «ООО Ромашка»
- **THEN** the request is refused as invalid, and no invitation is created in «ООО Ромашка»

### Requirement: FR-19 Administrator actions are closed to employees

Listing members, inviting, resending and revoking invitations, deactivating, reactivating and changing
roles SHALL be available only to administrators. For an employee these actions SHALL answer «not found»,
and the SPA SHALL NOT offer them. An employee's start page SHALL show their name, their organization
and «Выйти».

#### Scenario: An employee calls an administrator action
- **WHEN** Борис, an employee of «ООО Ромашка», asks for the members list, invites «gleb@romashka.test» or deactivates Анна
- **THEN** each request answers «not found» and nothing changes

#### Scenario: An employee opens the members page
- **WHEN** Борис opens «Участники» by its address
- **THEN** he sees «Страница не найдена», and his start page shows «Борис Иванов», «ООО Ромашка» and «Выйти» without «Участники»

### Requirement: FR-20 Actions from other sites are refused

A state-changing request SHALL be refused when it comes from a page of another site, even if the
browser sends the user's session along.

#### Scenario: A cross-site form
- **WHEN** Анна, signed in, opens a page of another site that submits a hidden form inviting «evil@attacker.test» to «ООО Ромашка»
- **THEN** the request is refused and no invitation is created
