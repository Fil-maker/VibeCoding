# mailboxes Specification

## Purpose
Lets a user connect the mailboxes they correspond from, keeps their passwords secret, and reads their
emails into the app without ever changing a mailbox.

## Requirements

### Requirement: FR-22 Connect a mailbox

A user SHALL connect a mailbox by giving the email address, the IMAP server, the port (993 by default)
and an app password; the login SHALL be the address unless the user gives another. Before saving, the
app SHALL sign in over an encrypted connection; only the installation's local test servers MAY be
reached without encryption. A failed sign-in SHALL save nothing and SHALL keep the picked service's
steps on view. One user SHALL NOT connect the same login on the same server twice.

#### Scenario: Successful connection
- **WHEN** Анна types «anna@yandex.ru», which fills the server «imap.yandex.ru» and the port 993, gives a valid app password and presses «Подключить»
- **THEN** the mailbox «anna@yandex.ru» appears on «Почтовые ящики» with the status «Ожидает чтения»

#### Scenario: Wrong password
- **WHEN** Анна connects «anna@yandex.ru» with a wrong app password
- **THEN** nothing is saved, the form shows «Не удалось войти в ящик: проверьте логин и пароль приложения» and keeps «Как подключить Яндекс Почту» with its link, and the address and the server stay filled

#### Scenario: Unreachable server
- **WHEN** Анна connects the server «imap.nowhere.test», which does not answer
- **THEN** nothing is saved and the form shows «Не удалось подключиться к серверу imap.nowhere.test»

#### Scenario: The same mailbox twice
- **WHEN** Анна connects «anna@yandex.ru» on «imap.yandex.ru» a second time
- **THEN** nothing is saved and the form shows «Этот ящик уже подключён»

#### Scenario: Empty fields
- **WHEN** Анна submits the form with an empty address, an empty server or password, or the port 0
- **THEN** nothing is saved, «Настройки сервера» open when a field there is invalid, and the form names each invalid field: «Укажите адрес почты», «Укажите сервер IMAP», «Укажите пароль приложения», «Порт должен быть от 1 до 65535»

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

Reading a mailbox and fetching an attachment from it SHALL open every folder read-only. Neither SHALL
mark an email as read, set or clear any flag, move, copy, delete or send an email in the mailbox.

#### Scenario: Unread emails stay unread
- **WHEN** Анна's Inbox holds 3 unread emails and the app reads the mailbox
- **THEN** the 3 emails are in the app and all 3 stay unread in the mailbox, and the mailbox holds the same emails in the same folders as before

#### Scenario: Downloading an attachment keeps the email unread
- **WHEN** an unread email with «договор.pdf» is in Анна's Inbox and she downloads «договор.pdf» in the app
- **THEN** the email stays unread with the same flags in the same folder of the mailbox

### Requirement: FR-26 A failed read is shown and retried

When a read fails, the mailbox SHALL show «Ошибка» with the reason in Russian, and the emails already
read SHALL stay. When the server refused the sign-in and the server belongs to a service that has
steps to connect, the mailbox SHALL also show «Как исправить», which opens that service's steps and
help link. The app SHALL try again at the next scheduled read or on «Обновить».

#### Scenario: The app password was revoked
- **WHEN** Анна revokes the app password in her mail service and the app reads the mailbox
- **THEN** the mailbox shows «Ошибка: не удалось войти в ящик, подключите его заново с новым паролем приложения» and her emails read before stay in «Переписка»

#### Scenario: The steps for a refused sign-in
- **WHEN** the mailbox «anna@yandex.ru» on «imap.yandex.ru» shows «Ошибка: не удалось войти в ящик…» and Анна presses «Как исправить»
- **THEN** she sees the steps of «Как подключить Яндекс Почту» and the link «Справка Яндекс Почты»

#### Scenario: No steps for an unknown server
- **WHEN** the mailbox «anna@studio-anna.ru» on «imap.studio-anna.ru» cannot sign in
- **THEN** it shows the error without «Как исправить»

#### Scenario: No steps for the demo mailbox
- **WHEN** the mailbox «anna@demo.test» on «greenmail» cannot sign in
- **THEN** it shows the error without «Как исправить»

#### Scenario: The server is down for a while
- **WHEN** the server does not answer at one read and answers 5 minutes later
- **THEN** the mailbox shows «Ошибка: сервер не отвечает» without «Как исправить» after the first read and «Прочитан» after the next one

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

### Requirement: FR-53 Pick the mail service from the address

The connect form SHALL pick the mail service from the domain of the typed address, ignoring case and
spaces, by the app's own list: Яндекс Почта, Mail.ru, Gmail, iCloud, Демо; any other domain SHALL pick
«Другой». A picked service SHALL fill the server and the port; «Другой» SHALL leave the server empty
with the port 993. The user SHALL change the service, the server, the port and the login by hand. The
address SHALL NOT be sent anywhere before «Подключить».

#### Scenario: A known domain
- **WHEN** Анна types «anna@yandex.ru» into «Адрес почты»
- **THEN** «Почтовый сервис» shows «Яндекс Почта», the server is «imap.yandex.ru», the port is 993 and the login is «anna@yandex.ru»

#### Scenario: Case and spaces
- **WHEN** Анна types « Anna@Mail.RU »
- **THEN** the service is «Mail.ru» and the server is «imap.mail.ru»

#### Scenario: An unknown domain
- **WHEN** Анна types «anna@studio-anna.ru»
- **THEN** the service is «Другой», «Настройки сервера» are open with an empty server and the port 993, and the form shows «Этот почтовый сервис нам незнаком. Адрес сервера IMAP и порт есть в справке вашей почты или у администратора домена.»

#### Scenario: A service without password sign-in
- **WHEN** Анна types «anna@outlook.com» or «anna@rambler.ru»
- **THEN** the service is «Другой» and the server is empty

#### Scenario: The demo mailbox
- **WHEN** Анна types «anna@demo.test»
- **THEN** the service is «Демо», the server is «greenmail» and the port is 3143

#### Scenario: Picking the service by hand
- **WHEN** Анна has typed «anna@studio-anna.ru» and picks «Gmail»
- **THEN** the server is «imap.gmail.com», the port is 993 and the login stays «anna@studio-anna.ru»

#### Scenario: The user's own server stays
- **WHEN** Анна has typed «anna@yandex.ru», changed the server to «imap.studio-anna.ru» under «Настройки сервера» and then corrects the address to «anna.k@yandex.ru»
- **THEN** the server stays «imap.studio-anna.ru» and the login becomes «anna.k@yandex.ru»

#### Scenario: The user's own port stays
- **WHEN** Анна has typed «anna@yandex.ru», changed the port to 143 under «Настройки сервера», corrected the address to «anna.k@yandex.ru» and connects
- **THEN** the port stays 143 and the request to connect carries the port 143

#### Scenario: A login other than the address
- **WHEN** Анна types «anna@studio-anna.ru», sets the login «anna» under «Настройки сервера» and connects
- **THEN** the mailbox appears on «Почтовые ящики» with the login «anna»

#### Scenario: Nothing leaves the app while typing
- **WHEN** Анна types «anna@studio-anna.ru» and does not press «Подключить»
- **THEN** the app sends no request carrying the address or its domain, neither to its own server nor to any other

### Requirement: FR-54 Show how to connect the service

Above the connect form the app SHALL say that it only reads the mailbox and why an app password is
needed. For a picked service other than «Демо» and «Другой» the form SHALL show «Как подключить
<service>»: the steps to turn on IMAP access where the service needs it and to create an app
password, and a link to the service's official help on its own domain, opened in a new tab and
carrying no part of the address.

#### Scenario: The explanation
- **WHEN** Анна opens «Почтовые ящики»
- **THEN** above the form she reads «Приложение только читает письма: не отправляет, не удаляет и не помечает их прочитанными. Для входа нужен пароль приложения — отдельный пароль для почтовых программ, который можно отозвать, не меняя основной.»

#### Scenario: Steps of Яндекс Почта
- **WHEN** the service is «Яндекс Почта»
- **THEN** the form shows «Как подключить Яндекс Почту» with the steps «Включите доступ по IMAP: Настройки → Почтовые программы → «С сервера imap.yandex.ru по протоколу IMAP» и «Пароли приложений и OAuth-токены».» and «Создайте пароль приложения для почты: Яндекс ID → Безопасность → Пароли приложений. Он начнёт действовать через 2–3 часа.», and the link «Справка Яндекс Почты» to a https page on yandex.ru

#### Scenario: Gmail needs no IMAP switch
- **WHEN** the service is «Gmail»
- **THEN** the steps say that IMAP is always on in Gmail, ask to turn on two-step verification and to create an app password, and the link leads to a https page on support.google.com

#### Scenario: Every real service has steps and a link
- **WHEN** the service is «Mail.ru», «Gmail» or «iCloud»
- **THEN** the form shows «Как подключить <service>» with at least one step and a https link on the service's own domain

#### Scenario: No steps for the demo and an unknown service
- **WHEN** the service is «Демо» or «Другой»
- **THEN** the form shows no «Как подключить» block and no help link

#### Scenario: The link carries no address
- **WHEN** Анна has typed «anna@yandex.ru» and opens «Справка Яндекс Почты»
- **THEN** the help page opens in a new tab and its address contains neither «anna» nor «anna@yandex.ru»
