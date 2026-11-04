# Mailbox connection hints

Date: 04.11.2026 · Task: 1.9 · Change: 1-9-mailbox-connection-hints

## Goal

Connecting a mailbox was hard: the user had to find the IMAP server and port, understand what an app
password is and learn where to create it. The form had four fields («Сервер IMAP», «Порт», «Логин»,
«Пароль приложения») with no hint and no link, and the errors of FR-22 and FR-26 were generic. The task
had two goals: (1) a mailbox connects without a search on the internet, because a built-in table maps
the domain of the address to a service, fills the server and the port and shows short steps with a link
to the official help; (2) a sign-in error says what to check in that service. No MX lookup and no
external catalogs.

## What was done

- Route: `/explore` chose hints plus detection by a built-in table (variants A and B without MX);
  both goals went into one `/feature`. The path was «New capability»: ADDED FR-53 and FR-54, MODIFIED
  FR-22 and FR-26; branch `feat/1-9-mailbox-connection-hints`, plan row 1.9, plan edition 0.21.
- Design session: the proposal, the delta spec of `mailboxes`, the design, the tasks and the handoff.
  The service table lives in the SPA (a separate endpoint was rejected: the data is constant and the
  address would be matched in the browser anyway). The mailbox's service in the list is found by its
  server, not by its login. Help links were read from the official pages on 04.11.2026.
- Backend: `GET /api/v1/mailboxes` returns `error_code` (`sign_in_failed`, `unreachable`,
  `read_failed`, or null), filled only for a mailbox in the error status; the password is still never
  returned. The API client was regenerated (and again at /finish, because the `Mailbox` docstring change
  altered the OpenAPI description).
- SPA: `mailServices.ts` (`MAIL_SERVICES`, `serviceForAddress`, `serviceForServer`), `ConnectForm.tsx`,
  `MailboxRow.tsx`, `ServiceSteps.tsx`, `mailboxesKey.ts`. The form starts with «Адрес почты»; server,
  port and login sit under «Настройки сервера»; services in the table are Яндекс Почта, Mail.ru, Gmail,
  iCloud and «Демо»; any other domain picks «Другой». Settings changed by hand survive an edit of the
  address. Above the form a line says the app only reads the mailbox and why an app password is needed.
- List: «Как исправить» shows the steps and the link for a refused sign-in on a service that has steps.
- Tests: backend `test_mailboxes_error_code.py` and extended `test_mailboxes_connect.py`; frontend
  `mailServices.test.ts`, `App.mailboxConnect.test.tsx`, `App.mailboxConnectErrors.test.tsx`,
  `App.mailboxFix.test.tsx`, `App.mailboxHowTo.test.tsx`, helper `mailboxForm.tsx`.
- Manual checks: all four help links answered HTTP 200 on 04.11.2026 and match the steps; the preview
  with GreenMail passed (known and unknown domains, Gmail by hand, a wrong demo password keeps the
  address, `anna@demo.test` goes to «Прочитан» with no «Как исправить»; no horizontal scroll at 360 px).
- /finish: `just check` 17 checks passed; tests 109 backend unit, 376 frontend unit, 319 database
  passed. The invariant review found no BLOCKER and two IMPORTANT (docs not yet synced, spec not yet
  archived), both resolved by archive and `/document`; two MINOR were dropped. At archive the merged
  FR-22 text exceeded 500 characters and was tightened without changing meaning, and the FR-26 line
  wrap was fixed. Docs updated: `docs/guide/frontend.md`, `docs/guide/mail-reading.md`,
  `docs/architecture.md`; `docs/domain.md` got the term «Mail service» and FR-53, FR-54;
  `docs/ideas.md` got two ideas (MX detection, more services in the hints; Outlook.com's absence noted).
  ADRs 0085–0096 were written.

## Key questions to the AI

- Which path for task 1.9? Recommended «New capability»; the user picked it.
- How should the form look? «Адрес первым (рекомендую)».
- How does the SPA know the kind of error? «Добавить error_code (рекомендую)».
- Should the table hold the demo domain? «Да, для показа (рекомендую)».
- Official Microsoft help says personal Outlook.com mailboxes accept only OAuth over IMAP since
  September 2024; what to do with Outlook? «Убрать из списка».
- Rambler's official help has no page on mail programs, so the server and steps could not be confirmed;
  what to do? «Убрать сейчас (рекомендую)».
- Approve the deltas with the Russian texts? «Да, одобряю (рекомендую)».
- During code: the demo mailbox («Демо», server greenmail) fails to sign in and would get a «Как
  исправить» button with nothing under it. «Скрыть кнопку (рекомендую)».
- FR-53 had no scenario for a hand-edited port and FR-26 none for the retry on «Обновить»; add them?
  «Добавить порт (рекомендую)».
- /finish: confirm the 12 decisions for ADRs? «Все подтверждаю (Recommended)».

## Decisions

| Decision | Alternatives | Reason | Who |
| --- | --- | --- | --- |
| Mailbox connection gets per-service hints and guide links plus server detection from the email domain by a built-in table, without MX lookup or external catalogs | hints only (A); detection via MX or Mozilla ISPDB; OAuth sign-in | А + Б, без внешних | [human] |
| Both goals (connect without searching: per-service hints and domain detection; errors that say what to fix per service) go into one /feature change | goal 1 now, goal 2 as /idea | Обе в /feature | [human] |
| Task 1.9 runs as a new capability: ADDED FR-53 connection hints, MODIFIED FR-22 and FR-26; feat, minor | changed behavior: only MODIFIED FR-22 and FR-26 | Новая возможность (рекомендую) | [human] |
| The connect form starts with «Адрес почты», which is also the login; server and port come from the service and sit under «Настройки сервера», open for «Другой»; a separate login is set there | all four fields always visible | Адрес первым (рекомендую) | [human] |
| GET /api/v1/mailboxes returns error_code (sign_in_failed, unreachable, read_failed) so the SPA shows the service steps only on a sign-in failure | SPA only: a guide link beside any mailbox error | Добавить error_code (рекомендую) | [human] |
| The service table holds «Демо» for demo.test: server greenmail, port 3143, no guide and no link | demo.test is an unknown domain | Да, для показа (рекомендую) | [human] |
| Outlook is left out of the service table: outlook.com, hotmail.com and live.com pick «Другой» | show Outlook with «пока нельзя» and a help link | Убрать из списка | [human] |
| Rambler is left out of the service table until its IMAP data is confirmed by an official page; rambler.ru picks «Другой» | keep Rambler with imap.rambler.ru:993 from memory, no steps, link to the help index | Убрать сейчас (рекомендую) | [human] |
| The login defaults to the full address for every service, though Yandex and Apple help pages name the part before @: chain participants exclude mailbox logins, so a bare name would show the user's own address as a counterparty | per-service login rule: the part before @ for Yandex and iCloud | chain participants are the addresses other than the logins of the user's mailboxes (ADR 0044); full address also signs in on Yandex and iCloud | [AI → accepted] |
| Approve change 1-9-mailbox-connection-hints: ADDED FR-53, FR-54; MODIFIED FR-22, FR-26 | - | Да, одобряю (рекомендую) | [human] |
| «Как исправить» is shown only for a refused sign-in on a service that has connection steps; the demo mailbox gets none | show the button for every known server | Скрыть кнопку (рекомендую) — у «Демо» нет шагов, под кнопкой было бы пусто | [human] |
| FR-53 gains a scenario for a port changed by hand; the retry on «Обновить» stays without a new scenario | leave both gaps in the handoff | Добавить порт (рекомендую) — повтор по «Обновить» уже проверяют тесты FR-24 | [human] |

## Mistakes and lessons

- The approved delta had two gaps that only the code step exposed: «Как исправить» would have shown an
  empty block for the demo mailbox, and a hand-edited port had no scenario. Both were fixed by changing
  the approved delta with the user's consent (decisions 11 and 12).
- The handoff said groups 1 and 2 would be coded one slice at a time; they were coded in one cycle in
  one sandbox because the interface of both was fixed beforehand. The handoff recorded the deviation.
- The Outlook and Rambler rows were in the first idea and the plan's «Done when» (outlook.com, rambler.ru
  as services); official pages showed Outlook no longer accepts app passwords and Rambler's data could
  not be confirmed, so the plan text had to be reworked after the user's answers.
- The plan row first said that «Другой» leaves the port empty; it was corrected to 993 before approval.
- The `Mailbox` docstring change altered the OpenAPI description, so the generated client had to be
  regenerated at /finish.
- At archive the merged FR-22 text exceeded 500 characters and had to be tightened.
- Not caught by this change: a wrong app password on connecting still answers HTTP 422 (behavior of
  task 1.2, unchanged); the encrypted sign-in clause of FR-22 has no behavioral test.

## What remains

- The steps for Mail.ru, Gmail and iCloud have no exact text in the spec; tests check their meaning
  and the https host. Help pages change over time, so the links need periodic checking.
- Ideas in `docs/ideas.md`: MX detection for own domains, more services in the hints (Outlook.com,
  Rambler once confirmed), OAuth sign-in.
- The retry on «Обновить» in FR-26 has no scenario of its own (FR-24 tests cover it).
- The architecture status still omits task 1.8 (left as found).
- The throwaway account `flow-1-9-hints@example.test` stays in the dev database (the app has no account
  deletion); the worktree has a gitignored `.env` copied from the main checkout.
