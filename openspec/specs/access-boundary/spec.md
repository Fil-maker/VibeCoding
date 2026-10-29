# access-boundary Specification

## Purpose
Keeps every user inside their own data: a signed-out visitor reaches nothing protected, actions from
other sites are refused, and one user never sees another user's data.

## Requirements

### Requirement: FR-17 Protected pages and actions need a signed-in user

Every page and action other than registration, confirmation, sign-in and password reset SHALL require a
signed-in user. A request without a valid session SHALL be refused as signed out. The SPA SHALL send
such a visitor to «Вход» and return them to the requested page after sign-in.

#### Scenario: A signed-out visitor opens a protected page
- **WHEN** a visitor who is not signed in opens the start page
- **THEN** they see «Вход», and after Анна signs in there she lands on the start page

#### Scenario: A forged or ended session
- **WHEN** a request carries a session token that never existed or belongs to a session ended by sign-out
- **THEN** it is refused as signed out and no data is returned

### Requirement: FR-20 Actions from other sites are refused

A state-changing request SHALL be refused when it comes from a page of another site, even if the
browser sends the user's session along.

#### Scenario: A cross-site form
- **WHEN** Анна, signed in, opens a page of another site that submits a hidden form signing her out
- **THEN** the request is refused and her session stays

### Requirement: FR-21 Users never see each other

Every piece of data SHALL belong to exactly one user. Every page and action SHALL work only with the
data of the signed-in user, taken from the session, never from the request. Data of another user SHALL
answer «not found», the same answer as for data that does not exist.

#### Scenario: A user gets only their own profile
- **WHEN** Вера and Анна are both signed in and Вера asks for the profile of the signed-in user
- **THEN** she gets «Вера Смирнова» and her own email, and nothing of Анна's

#### Scenario: A user named in the request is refused
- **WHEN** Вера requests a password reset with a request that also names Анна's user identifier
- **THEN** the request is refused as invalid and no reset email goes out
