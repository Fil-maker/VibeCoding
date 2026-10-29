# mailboxes Specification

## Purpose
Lets a user connect the mailboxes they correspond from, keeps their passwords secret, and reads their
emails into the app without ever changing a mailbox.

## Requirements

### Requirement: FR-22 Connect a mailbox

A user SHALL connect a mailbox by giving the IMAP server, the port (993 by default), the login and an
app password. Before saving, the app SHALL sign in to the server over an encrypted connection; only
servers the installation lists as local test servers MAY be reached without encryption. A failed
sign-in SHALL save nothing. One user SHALL NOT connect the same login on the same server twice.

#### Scenario: Successful connection
- **WHEN** Анна connects the server «imap.yandex.ru», port 993, login «anna@yandex.ru» and a valid app password
- **THEN** the mailbox «anna@yandex.ru» appears on «Почтовые ящики» with the status «Ожидает чтения»

#### Scenario: Wrong password
- **WHEN** Анна connects «anna@yandex.ru» with a wrong app password
- **THEN** nothing is saved and the form shows «Не удалось войти в ящик: проверьте логин и пароль приложения»

#### Scenario: Unreachable server
- **WHEN** Анна connects the server «imap.nowhere.test», which does not answer
- **THEN** nothing is saved and the form shows «Не удалось подключиться к серверу imap.nowhere.test»

#### Scenario: The same mailbox twice
- **WHEN** Анна connects «anna@yandex.ru» on «imap.yandex.ru» a second time
- **THEN** nothing is saved and the form shows «Этот ящик уже подключён»

#### Scenario: Empty fields
- **WHEN** Анна submits the form with an empty server, login or password, or the port 0
- **THEN** nothing is saved and the form names each invalid field: «Укажите сервер IMAP», «Укажите логин», «Укажите пароль приложения», «Порт должен быть от 1 до 65535»

### Requirement: FR-23 Keep the mailbox password secret

The app SHALL store a mailbox password only in encrypted form and SHALL never show it or send it back
in any answer. The list of mailboxes SHALL show for each mailbox its login, server, status and the
time of its last successful read.

#### Scenario: The password is never shown
- **WHEN** Анна, who connected «anna@yandex.ru» with the app password «app-pass-1234», opens «Почтовые ящики»
- **THEN** she sees «anna@yandex.ru», «imap.yandex.ru» and the status, and no answer of the app contains «app-pass-1234»

#### Scenario: Another user's mailboxes
- **WHEN** Вера opens «Почтовые ящики» while Анна has connected «anna@yandex.ru»
- **THEN** Вера sees only her own mailboxes and the text «Ящики ещё не подключены» when she has none

### Requirement: FR-24 Read the mailboxes

The app SHALL read the folders Inbox and Sent of every connected mailbox, the emails of the last 12
months: right after connecting, then every 5 minutes, and when the user presses «Обновить». A read
SHALL add only the emails not read before. While a read runs the mailbox SHALL show «Читается»; after
it, «Прочитан» with the date and time.

#### Scenario: First read after connecting
- **WHEN** Анна connects a mailbox whose Inbox holds 30 emails of this year and 5 emails of two years ago, and whose Sent holds 10 emails of this year
- **THEN** after the read 40 emails are in the app and the mailbox shows «Прочитан» with the time of the read

#### Scenario: A new email after «Обновить»
- **WHEN** a new email arrives in Анна's Inbox and she presses «Обновить» for that mailbox
- **THEN** after the read the new email is in the app and no earlier email is added a second time

#### Scenario: A new email without any action
- **WHEN** a new email arrives in Анна's Inbox and 5 minutes pass
- **THEN** the email is in the app without Анна pressing anything

#### Scenario: Refreshing another user's mailbox
- **WHEN** Вера presses «Обновить» with the identifier of Анна's mailbox
- **THEN** the answer is «not found» and Анна's mailbox is not read

### Requirement: FR-25 Reading never changes the mailbox

Reading SHALL open every folder read-only. It SHALL NOT mark an email as read, set or clear any flag,
move, copy, delete or send an email in the mailbox.

#### Scenario: Unread emails stay unread
- **WHEN** Анна's Inbox holds 3 unread emails and the app reads the mailbox
- **THEN** the 3 emails are in the app and all 3 stay unread in the mailbox, and the mailbox holds the same emails in the same folders as before

### Requirement: FR-26 A failed read is shown and retried

When a read fails, the mailbox SHALL show «Ошибка» with the reason in Russian, and the emails already
read SHALL stay. The app SHALL try again at the next scheduled read or on «Обновить».

#### Scenario: The app password was revoked
- **WHEN** Анна revokes the app password in her mail service and the app reads the mailbox
- **THEN** the mailbox shows «Ошибка: не удалось войти в ящик, подключите его заново с новым паролем приложения» and her emails read before stay in «Переписка»

#### Scenario: The server is down for a while
- **WHEN** the server does not answer at one read and answers 5 minutes later
- **THEN** the mailbox shows «Ошибка: сервер не отвечает» after the first read and «Прочитан» after the next one

### Requirement: FR-27 Disconnect a mailbox

The user SHALL disconnect a mailbox after confirming. Disconnecting SHALL delete its password and stop
reading it; the emails and reply chains read from it SHALL stay. Connecting the same mailbox again
SHALL resume reading without adding an email twice.

#### Scenario: Disconnecting keeps the emails
- **WHEN** Анна disconnects «anna@yandex.ru» and confirms «Отключить ящик anna@yandex.ru? Прочитанные письма останутся.»
- **THEN** the mailbox disappears from «Почтовые ящики», it is no longer read, and its emails stay in «Переписка»

#### Scenario: Connecting again
- **WHEN** Анна connects «anna@yandex.ru» again a day after disconnecting it
- **THEN** the emails that arrived meanwhile are added and no email appears twice

#### Scenario: Disconnecting another user's mailbox
- **WHEN** Вера disconnects a mailbox by the identifier of Анна's mailbox
- **THEN** the answer is «not found» and Анна's mailbox stays connected
