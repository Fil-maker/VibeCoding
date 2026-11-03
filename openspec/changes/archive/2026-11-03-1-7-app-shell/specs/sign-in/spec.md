# Spec Delta

## MODIFIED Requirements

### Requirement: FR-6 Session lifetime and sign-out

A sign-in SHALL start a session that lasts 14 days. Signing out SHALL end the session at once. An ended
or expired session SHALL be treated as signed out: «/» shows the landing page and a protected page sends
the visitor to «Вход». A session SHALL NOT be readable by the page's scripts.

#### Scenario: Sign-out
- **WHEN** Анна presses «Выйти» and then opens «Проекты»
- **THEN** she first sees the landing page, and then the page «Вход»

#### Scenario: Expired session
- **WHEN** Анна signed in 15 days ago and opens «Проекты»
- **THEN** she sees the page «Вход»

#### Scenario: Sign-out on one device keeps the other
- **WHEN** Анна is signed in on a laptop and a phone and signs out on the laptop
- **THEN** she stays signed in on the phone
