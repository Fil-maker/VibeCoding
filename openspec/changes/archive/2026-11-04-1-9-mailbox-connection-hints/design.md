# Design

## Context

Task 1.2 built the connect form in `frontend/src/features/mailboxes/MailboxesPage.tsx` (198 lines):
an uncontrolled form with «Сервер IMAP», «Порт» (993), «Логин», «Пароль приложения», posted to
`POST /api/v1/mailboxes` (`MailboxConnect {server, port, login, password}`). The list
(`GET /api/v1/mailboxes`) gives `Mailbox {id, server, port, login, status, error, last_read_at}`;
`error` is the Russian reason built by `describe_status_error` from `mailboxes.error_code`
(`sign_in_failed`, `unreachable`, `read_failed`), and the code itself is not returned.

The official help pages were read on 04.11.2026 (decisions 7–9 of this change rest on them):

| Service | Server, port | Help link | Source facts |
|---|---|---|---|
| Яндекс Почта | imap.yandex.ru, 993 | https://yandex.ru/support/yandex-360/customers/mail/ru/mail-clients/others | IMAP and «Пароли приложений и OAuth-токены» are turned on under «Почтовые программы»; the app password is created in Яндекс ID → Безопасность → Пароли приложений and starts working in 2–3 hours |
| Mail.ru | imap.mail.ru, 993 | https://help.mail.ru/mail/login/mailer/ | a password for an external app is required: Настройки → Все настройки → Безопасность → Пароли для внешних приложений; a phone must be linked |
| Gmail | imap.gmail.com, 993 | https://support.google.com/accounts/answer/185833?hl=ru | IMAP is always on; an app password needs 2-Step Verification; created at myaccount.google.com/apppasswords. The host is common knowledge, not on the pages read |
| iCloud | imap.mail.me.com, 993 | https://support.apple.com/ru-ru/102654 | an app-specific password is required and needs two-factor authentication; account.apple.com → Вход и безопасность → Пароли приложений |

Domains of each service: Яндекс Почта — yandex.ru, ya.ru, yandex.com; Mail.ru — mail.ru, inbox.ru,
list.ru, bk.ru, internet.ru; Gmail — gmail.com, googlemail.com; iCloud — icloud.com, me.com, mac.com;
Демо — demo.test.

Outlook.com accepts only OAuth over IMAP since 16.09.2024 and Rambler's help has no mail-program
page; both stay out (decisions 7, 8).

## Goals / Non-Goals

**Goals:**
- A user of the four listed services connects by typing the address and an app password only.
- Every listed service tells where to turn on IMAP and create an app password, with an official link.
- A refused sign-in, on connecting and in the list, points at those steps.

**Non-Goals:**
- MX lookup, autoconfig, ISPDB or any request to resolve the server.
- Checking that a help link still loads.
- Storing the address apart from the login.

## Decisions

**The service table lives in the SPA, not in the backend.** It is UI text and static data; the SPA
picks the service as the user types, so no request carries the address (FR-53 «Nothing leaves the
app while typing»). *Alternative:* `GET /api/v1/mail-services` — one more endpoint for constant data,
and a typed address would still be matched in the browser.

**The service of a listed mailbox is found by its server, not its login.** A mailbox stores only
server and login; the server names the service (`imap.yandex.ru` → Яндекс Почта) even when the login
is not an address. An unknown server gives no steps (FR-26 «No steps for an unknown server»).

**The list answer gains `error_code`.** The SPA shows «Как исправить» only for `sign_in_failed`
(decision 5). *Alternative:* match the Russian error text — breaks on any wording change.

**The login follows the address until the user edits it; so do the server and the port.** Each of the
three fields keeps a «edited by hand» mark; typing the address or picking a service overwrites only
unmarked fields (FR-53 «The user's own server stays»). The default login is the full address for
every service (decision 9). *Alternative:* overwrite always — loses the user's edits.

**Picking a service by hand is kept until the address's domain changes.** A hand pick of «Gmail» for
«anna@studio-anna.ru» stays while the user edits the part before «@»; a new domain picks again.

**«Настройки сервера» is a disclosure (`<details>`).** Closed for a picked service, open for
«Другой», and opened when the server answers with an error on «server», «port» or a hand-edited
«login». An error on «login» while the login follows the address is shown on «Адрес почты» as
«Укажите адрес почты».

**The page is split into files** to stay under 300 lines: `MailboxesPage.tsx` (page and list),
`MailboxRow.tsx`, `ConnectForm.tsx`, `ServiceSteps.tsx` (the «Как подключить» block, reused by
«Как исправить»), `mailServices.ts` (the table and the two lookups).

**Help links open with `target="_blank" rel="noopener noreferrer"`** and are constants, so no part
of the address reaches them (FR-54 «The link carries no address»).

**«Демо» is in the table** with server `greenmail`, port 3143, no steps and no link (decision 6). It
works only where `IMAP_INSECURE_HOSTS` lists `greenmail`, as compose does.

## Interface

API (`GET /api/v1/mailboxes`, each item):

```
Mailbox {
  id, server, port, login, status, error, last_read_at   // unchanged
  error_code: "sign_in_failed" | "unreachable" | "read_failed" | null
                                // null unless status is "failed"
}
```

`POST /api/v1/mailboxes` and its errors are unchanged.

SPA, `frontend/src/features/mailboxes/mailServices.ts`:

```ts
type MailServiceId = 'yandex' | 'mailru' | 'gmail' | 'icloud' | 'demo' | 'other';

interface MailService {
  id: MailServiceId;
  name: string;            // «Яндекс Почта», «Mail.ru», «Gmail», «iCloud», «Демо», «Другой»
  howToTitle: string | null; // «Как подключить Яндекс Почту»; null for demo and other
  server: string;          // '' for other
  port: number;            // 993; 3143 for demo
  steps: readonly string[]; // [] for demo and other
  help: { label: string; url: string } | null;
}

const MAIL_SERVICES: readonly MailService[];
function serviceForAddress(address: string): MailService;    // trims, lowercases the domain; 'other' if unknown
function serviceForServer(server: string): MailService | null; // null if no service has this server
```

Form controls, by accessible name: «Адрес почты», «Почтовый сервис» (select), «Настройки сервера»
(disclosure) holding «Сервер IMAP», «Порт», «Логин»; «Пароль приложения»; «Подключить». The
«Как подключить <service>» block is a region named by its title, holding the steps as a list and the
help link. The list row of a mailbox failed with `sign_in_failed` on a server of a service with steps
has the button «Как исправить»; «Демо» has no steps and so no button.

## Test seams

- Backend: the HTTP API `GET /api/v1/mailboxes` with `FakeMailReader` — `error_code` per status.
- SPA: `MailboxesPage` rendered with a mocked API client (as `App.mailboxes.test.tsx` does) —
  every FR-53, FR-54, FR-22 and FR-26 scenario; the mocked `fetch` proves no request while typing.
- `mailServices.ts` lookups as plain unit tests: every domain of the table, case and spaces, unknown
  domains, every server.

## Risks / Trade-offs

- [A service changes its menus or help URL] → the steps go stale silently. Mitigation: the source
  table above with its date; a stale link is a `/fix`.
- [A custom domain on Яндекс 360 or Google Workspace picks «Другой»] → the user types the server or
  picks the service by hand; MX lookup is deferred to `docs/ideas.md`.
- [A user picks a login that is not an address] → their own address may show as a counterparty
  (chain participants exclude mailbox logins); accepted, it is a deliberate choice under «Настройки
  сервера».
- No migration and no rollback concern: `error_code` already exists in the table; the API adds a
  field, which old clients ignore.
