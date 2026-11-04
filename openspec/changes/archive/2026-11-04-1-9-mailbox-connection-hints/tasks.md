# Tasks

One code cycle (`.claude/skills/feature/code-step.md`) per slice, each with its own sandbox, red check
and `close`: group 1 (backend, `error_code`), group 2 (SPA, FR-53, FR-54, FR-22, FR-26). `test-writer`
writes the slice's tests from the brief; `code-writer` writes the slice's code. Tests sit only at the
seams of design «Test seams». Implementation docs are updated at `/finish` through `/document`;
product docs in group 3.

## 1. Error code in the mailbox list

- [x] 1.1 `Mailbox` schema gains `error_code: MailboxErrorCode | None`, set by `to_mailbox_view` from the row only when the status is `failed`; `just api-client` regenerates the client — check - `just check` passes, including the client freshness check
- [x] 1.2 Scenario tests (`test-writer`, sandbox), through the HTTP API: a mailbox refused at a read → `error_code` «sign_in_failed»; an unreachable server → «unreachable»; a read error → «read_failed»; a `pending` and a `read` mailbox → null; a mailbox read again successfully after a failure → null; no answer contains the app password; Вера's list holds no item of Анна — check - red before the code, green after `tdd_sandbox.py close`

## 2. Connect form and hints (SPA)

- [x] 2.1 `mailServices.ts` with the table of design «Context» and the lookups of «Interface»; `ServiceSteps.tsx`; `ConnectForm.tsx` per design «Decisions» with the exact Russian texts of the deltas; `MailboxRow.tsx` with «Как исправить» for `sign_in_failed` on a known server; `MailboxesPage.tsx` with the explanation above the form; every file under 300 lines — check - `pnpm --dir frontend lint`, `typecheck`, `build` pass
- [x] 2.2 Unit tests (`test-writer`, sandbox) for `serviceForAddress` and `serviceForServer`: each domain of the table (yandex.ru, ya.ru, yandex.com, mail.ru, inbox.ru, list.ru, bk.ru, internet.ru, gmail.com, googlemail.com, icloud.com, me.com, mac.com, demo.test), case and spaces, outlook.com, rambler.ru, an address without «@», an empty string; each server and an unknown one — check - red before the code, green after `close`
- [x] 2.3 Component tests (`test-writer`, sandbox) on `MailboxesPage` with a mocked API: every scenario of FR-53, FR-54, FR-22 and FR-26 in the deltas, with the exact texts; the request body of «Подключить» for a known service, a hand-picked service and a login set by hand; no `fetch` call while typing an address; help links with `target="_blank"`, `rel` holding «noopener», a https URL on the service's domain and no part of the address — check - red before the code, green after `close`

## 3. Product docs

- [x] 3.1 `docs/domain.md`: glossary «Mail service» (a service of the built-in list, picked by the address's domain; «Другой» otherwise); requirements map row `mailboxes` gains FR-53, FR-54; «Last FR number: FR-54» at archive — check - `just check` doc facts pass
- [x] 3.2 `docs/ideas.md`: add «Server detection by MX record» (custom domains on Яндекс 360 and Google Workspace; the domain leaves the app to DNS) and «More mail services in the connection hints» (Рамблер once its official help confirms the server and the steps); in «OAuth sign-in to Gmail and Outlook» note that Outlook.com is left out of the hints for this reason — check - the entries are as stated

## 4. Verification

- [x] 4.1 `just check` passes — check - all PASS
- [x] 4.2 `/test` with `all` passes — check - backend unit, backend database and frontend suites report counts, none NOT PRESENT
- [x] 4.3 Each help link of the table loads its page — check - `web-fetch` reports HTTP 200 with the expected topic for all four links; a failed one is replaced from the service's official help before finish
- [x] 4.4 Manual flow (`flow-checker`, preview + GreenMail after `just demo-mail`): sign up a throwaway `flow-1-9-hints@example.test`; on «Почтовые ящики» read the explanation; type «anna@yandex.ru» → «Яндекс Почта», «Как подключить Яндекс Почту» with the link; type «anna@studio-anna.ru» → «Другой» with «Настройки сервера» open and the hint; type «anna@demo.test» and the demo password → «Подключить» → the mailbox reads to «Прочитан …»; try «anna.work@demo.test» with a wrong password → the sign-in error; at 360 px the form reads without horizontal scrolling — check - its PASS report; test data cleaned up

## 5. Done when

- [x] 5.1 On «Почтовые ящики» the connect form starts with «Адрес почты». An address on yandex.ru, mail.ru, gmail.com, icloud.com or demo.test picks its service and fills the server and port — check - 4.4 and the FR-53 tests
- [x] 5.2 The user can change the service by hand; «Другой» leaves the server open and empty and the port 993, with a hint where to find the server, and an unknown domain, outlook.com and rambler.ru among them, picks «Другой» — check - 4.4 and the FR-53 tests
- [x] 5.3 Under «Настройки сервера» the user can change the server and port and set a login other than the address — check - the FR-53 tests
- [x] 5.4 Every service except «Демо» and «Другой» shows the steps «включить IMAP» and «создать пароль приложения» and a https link to its official help — check - 4.3 and the FR-54 tests
- [x] 5.5 Above the form the page says why an app password is needed and that the app only reads the mailbox — check - 4.4 and the FR-54 tests
- [x] 5.6 A sign-in failure on connecting and «не удалось войти в ящик» in the list show the steps and the link of the mailbox's service; «сервер не отвечает» does not — check - the FR-22 and FR-26 tests
- [x] 5.7 The answer of GET /api/v1/mailboxes carries error_code and still never the password — check - the group 1 tests
- [x] 5.8 Picking the service sends no request to any external service — check - the FR-53 «Nothing leaves the app while typing» test
- [x] 5.9 `just check` and `just test-all` pass — check - 4.1 and 4.2
