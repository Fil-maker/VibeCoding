# Spec Delta

## MODIFIED Requirements

### Requirement: FR-17 Protected pages and actions need a signed-in user

Every page and action other than the landing page, registration, confirmation, sign-in and password
reset SHALL require a signed-in user. A request without a valid session SHALL be refused as signed out.
The SPA SHALL send such a visitor to «Вход» and return them to the requested page after sign-in.

#### Scenario: A signed-out visitor opens a protected page
- **WHEN** a visitor who is not signed in opens «Проекты»
- **THEN** they see «Вход», and after Анна signs in there she lands on «Проекты»

#### Scenario: A forged or ended session
- **WHEN** a request carries a session token that never existed or belongs to a session ended by sign-out
- **THEN** it is refused as signed out and no data is returned
