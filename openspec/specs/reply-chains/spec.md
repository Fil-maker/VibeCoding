# reply-chains Specification

## Purpose
Joins the emails of all of a user's mailboxes into reply chains, each email stored once, so that the user
reads a whole exchange in one place and later placement works with whole chains.

## Requirements

### Requirement: FR-28 Every email is stored once

An email SHALL be stored once per user, however many of the user's mailboxes and folders hold it. Two
copies SHALL count as one email when their `Message-ID` is equal. An email without a `Message-ID`
SHALL count as one email only within the folder it was read from.

#### Scenario: An email in two mailboxes
- **WHEN** Анна sends an email from «anna@yandex.ru» to «anna@mail.ru», both her connected mailboxes, and both are read
- **THEN** «Переписка» shows that email once

#### Scenario: Two users receive the same email
- **WHEN** one email from «oleg@stroy.test» goes to both Анна and Вера, and both of their mailboxes are read
- **THEN** each of them sees the email once in their own «Переписка», and Вера's chain lists only her own participants and emails

### Requirement: FR-29 Join emails into reply chains

The app SHALL join a user's emails into reply chains: an email whose `In-Reply-To` or `References`
names another email of the user SHALL be in that email's chain, whichever mailbox holds either of them.
An email that names emails of two chains SHALL join them into one. An email that names no known email
SHALL start its own chain, even when its subject repeats another one.

#### Scenario: A reply from another mailbox joins the chain
- **WHEN** Олег writes to «anna@yandex.ru» and Анна answers him from «anna@mail.ru» with «In-Reply-To» of his email
- **THEN** both emails are in one reply chain

#### Scenario: A reply read before its original
- **WHEN** the reply of Анна is read first and Олег's original email is read at a later read
- **THEN** after the later read both emails are in one reply chain

#### Scenario: An email links two chains
- **WHEN** Анна has two chains and a new email names one email of each in its «References»
- **THEN** after the read the three emails are in one reply chain

#### Scenario: The same subject without reply headers
- **WHEN** two emails with the subject «Смета на 2027 год» name no other email
- **THEN** they are in two separate reply chains

### Requirement: FR-30 List the reply chains

«Переписка» SHALL list the user's reply chains, the chain with the latest email first, 50 per page.
Each chain SHALL show the subject of its first email, its participants other than the user, the
number of emails and the date of its latest email. The user's own addresses are the logins of their
mailboxes and their account email.

#### Scenario: The list of chains
- **WHEN** Анна has a chain «Договор поставки» of 4 emails with «oleg@stroy.test», the latest on 28.10.2026, and a chain «Смета» of 2 emails with «ira@design.test», the latest on 20.10.2026
- **THEN** «Переписка» shows «Договор поставки» first with «oleg@stroy.test», «4 письма» and «28.10.2026», then «Смета» with «ira@design.test», «2 письма» and «20.10.2026»

#### Scenario: No emails yet
- **WHEN** Вера has connected no mailbox
- **THEN** «Переписка» shows «Писем пока нет: подключите почтовый ящик»

### Requirement: FR-31 Read a reply chain

Opening a reply chain SHALL show its emails from the oldest to the newest, each with the sender, the
recipients, the date, the subject, the text and the names of its attachments. An email with only an
HTML part SHALL be shown as plain text without markup or scripts. Another user's chain SHALL answer
«not found».

#### Scenario: Reading a chain
- **WHEN** Анна opens the chain «Договор поставки»
- **THEN** she sees its 4 emails from the oldest to the newest, each with the sender, recipients, date, text and the attachment name «договор.pdf» on the email that carried it

#### Scenario: An HTML-only email
- **WHEN** the chain holds an email whose only part is HTML with «<b>Срок</b> — пятница<script>alert(1)</script>»
- **THEN** its text shows «Срок — пятница» and no script runs

#### Scenario: Another user's chain
- **WHEN** Вера opens a chain by the identifier of a chain of Анна
- **THEN** she sees «Страница не найдена» and the answer to the request is «not found»
