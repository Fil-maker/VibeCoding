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
recipients, the date, the subject, the text and its attachments. Each attachment SHALL show its name, its
type as the file extension in capitals and its size; an attachment of an email read before sizes were
kept SHALL show no size. An email with only an HTML part SHALL be shown as plain text without markup or
scripts. Another user's chain SHALL answer «not found».

#### Scenario: Reading a chain
- **WHEN** Анна opens the chain «Договор поставки»
- **THEN** she sees its 4 emails from the oldest to the newest, each with the sender, recipients, date, text and the attachment «договор.pdf · PDF · 1,2 МБ» on the email that carried a file of 1 258 291 bytes

#### Scenario: Small and nameless types
- **WHEN** an email carries «смета.xlsx» of 812 bytes and «README» of 45 000 bytes
- **THEN** the page shows «смета.xlsx · XLSX · 812 Б» and «README · 44 КБ»

#### Scenario: An attachment read before sizes were kept
- **WHEN** the email with «акт.pdf» was read before the app kept the sizes of attachments
- **THEN** the page shows «акт.pdf · PDF» without a size, and it can be downloaded

#### Scenario: An HTML-only email
- **WHEN** the chain holds an email whose only part is HTML with «<b>Срок</b> — пятница<script>alert(1)</script>»
- **THEN** its text shows «Срок — пятница» and no script runs

#### Scenario: Another user's chain
- **WHEN** Вера opens a chain by the identifier of a chain of Анна
- **THEN** she sees «Страница не найдена» and the answer to the request is «not found»

### Requirement: FR-57 Download an attachment

A click on an attachment SHALL download the file under its own name with the same bytes as in the
mailbox. The app SHALL fetch it from a connected mailbox that holds a copy of the email and SHALL NOT keep
the content after the download. The file SHALL always be offered for saving, never opened inside the
app. An attachment of another user's email SHALL answer «not found».

#### Scenario: Downloading a contract
- **WHEN** Анна clicks «договор.pdf» on an email of the chain «Договор поставки» held by her connected mailbox «anna@yandex.ru»
- **THEN** her browser saves «договор.pdf», byte for byte the file attached to that email in the mailbox

#### Scenario: Two attachments with one name
- **WHEN** an email carries two files both named «скан.jpg», and Анна clicks the second one
- **THEN** the browser saves the second file, not the first

#### Scenario: The email is in two mailboxes, one disconnected
- **WHEN** the email is held by «anna@yandex.ru», now disconnected, and by «anna@mail.ru», connected
- **THEN** a click on its attachment downloads the file from «anna@mail.ru»

#### Scenario: Downloading twice
- **WHEN** Анна downloads «договор.pdf» twice
- **THEN** both files are the same, and the app keeps no copy of the content

#### Scenario: An HTML attachment
- **WHEN** Анна clicks the attachment «счёт.html» whose content holds «<script>alert(1)</script>»
- **THEN** the browser saves «счёт.html» and no script of it runs in the app

#### Scenario: Another user's attachment
- **WHEN** Вера asks for an attachment by the identifier of an email of Анна
- **THEN** the answer is «not found» and the app does not connect to Анна's mailbox

### Requirement: FR-58 An attachment that cannot be fetched

When an attachment cannot be fetched, the page SHALL show the reason in Russian under that attachment and
nothing SHALL be downloaded. The status of the mailbox SHALL NOT change because of a failed download.

#### Scenario: No connected mailbox holds the email
- **WHEN** Анна clicks an attachment of an email held only by her disconnected mailbox «anna@yandex.ru»
- **THEN** the page shows «Файл недоступен: ящик отключён» under the attachment

#### Scenario: The email is gone from the mailbox
- **WHEN** Анна deleted the email in her mail service and then clicks its attachment in the app
- **THEN** the page shows «Письмо больше не найдено в ящике» under the attachment, and the email stays in «Переписка»

#### Scenario: The server refuses the sign-in
- **WHEN** Анна revoked the app password of «anna@yandex.ru» and clicks an attachment of an email held only by it
- **THEN** the page shows «Не удалось получить файл: не удалось войти в ящик» under the attachment, and «Почтовые ящики» shows the same status for the mailbox as before the click

#### Scenario: The server does not answer
- **WHEN** the server of the mailbox does not answer when Анна clicks an attachment
- **THEN** the page shows «Не удалось получить файл: сервер не отвечает» under the attachment, and a later click downloads the file once the server answers
