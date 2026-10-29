# Spec Delta

## RENAMED Requirements

- FROM: `### Requirement: FR-1 Register an organization`
- TO: `### Requirement: FR-1 Register a user`

## MODIFIED Requirements

### Requirement: FR-1 Register a user

A visitor SHALL register as a user by giving their name (1–200 characters), their email and a password
of 10–128 characters. The app SHALL create a user who is not confirmed yet and belongs to no
organization. It SHALL send a confirmation email to that address. The email is compared without regard
to case and surrounding spaces. An email SHALL belong to at most one user of the installation.

#### Scenario: Successful registration
- **WHEN** a visitor registers with the name «Анна Петрова», the email «Anna@Romashka.test» and the password «correct-horse-1»
- **THEN** a user «Анна Петрова» exists whose email is «anna@romashka.test», not confirmed
- **AND** one confirmation email goes to «anna@romashka.test»
- **AND** the page shows «Мы отправили письмо со ссылкой для подтверждения на anna@romashka.test»

#### Scenario: Email already belongs to a confirmed user
- **WHEN** a visitor registers with «anna@romashka.test», which belongs to a confirmed user
- **THEN** no user is created or changed and the form shows «Этот email уже зарегистрирован»

#### Scenario: The mail server is unavailable
- **WHEN** a visitor registers as «Анна Петрова» while the mail server refuses connections
- **THEN** the page shows «Не удалось отправить письмо. Попробуйте зарегистрироваться ещё раз позже», and a repeated registration with the same email is accepted

#### Scenario: Invalid input
- **WHEN** a visitor registers with an empty name, an email without «@» or the password «short»
- **THEN** nothing is created and the form names each invalid field: «Укажите имя», «Укажите корректный email», «Пароль должен быть от 10 до 128 символов»

#### Scenario: An organization name is refused
- **WHEN** a request to register carries an organization name besides the name, the email and the password
- **THEN** the request is refused as invalid and no user is created

### Requirement: FR-2 Confirm the registrant's email

A registrant SHALL become able to sign in only after following the confirmation link. The link SHALL be
single-use and valid for 24 hours. Until confirmation the app SHALL refuse the registrant's sign-in.

#### Scenario: Confirmation by a valid link
- **WHEN** Анна follows the confirmation link 2 hours after registering
- **THEN** her email is confirmed, she is signed in and lands on the start page, which shows «Анна Петрова» and «Выйти» and no organization

#### Scenario: Sign-in before confirmation
- **WHEN** Анна signs in with the right password before following the link
- **THEN** sign-in is refused with «Подтвердите email: ссылка в письме, которое мы отправили»

#### Scenario: Expired or used link
- **WHEN** Анна follows the confirmation link 25 hours after registering, or follows it a second time
- **THEN** nothing changes and the page shows «Ссылка недействительна или устарела»

### Requirement: FR-3 Repeat an unconfirmed registration

A registration whose email is not confirmed SHALL NOT block that email. A new registration with the
same email SHALL replace the unconfirmed user. It SHALL send a new confirmation link, and the earlier
links SHALL stop working.

#### Scenario: The registrant registers again
- **WHEN** Анна registered as «Анна» yesterday without confirming and today registers as «Анна Петрова» with the same email
- **THEN** only one user «Анна Петрова» exists for her email, a new confirmation email goes out, and yesterday's link shows «Ссылка недействительна или устарела»
