# The login defaults to the full address for every service, though Yandex and Apple help pages name the part before @: chain participants exclude mailbox logins, so a bare name would show the user's own address as a counterparty

Id: 0093 · Date: 04.11.2026 · Kind: technical · Status: Accepted · Who: [AI → accepted]

## Context
Task: 1.9.
- GET /api/v1/mailboxes items gain error_code: sign_in_failed, unreachable or read_failed when the status is failed, else null; computed in service.py _failed_error_code; the password is never in any answer
- frontend/src/features/mailboxes/mailServices.ts holds the built-in table of mail services (Яндекс Почта, Mail.ru, Gmail, iCloud, Демо for demo.test on greenmail:3143) with domains, server, port, steps and a constant https help link; any other domain is «Другой» with an empty server and port 993; matching is local, no request
- MailboxesPage.tsx was split: ConnectForm.tsx (the connect form: «Адрес почты» first, «Почтовый сервис», «Настройки сервера» with server, port and login, hand-edited server and port stay when the address changes), MailboxRow.tsx (one mailbox row with «Как исправить» for error_code sign_in_failed on a server of a service with steps), ServiceSteps.tsx (the region «Как подключить <service>» with the steps as a list and the help link opened in a new tab with rel noopener noreferrer), mailboxesKey.ts (MAILBOXES_KEY, the query key StartPage also imports)
- frontend/src/test/mailboxForm.tsx is a test helper that fills the connect form for the SPA tests

## Decision
The login defaults to the full address for every service, though Yandex and Apple help pages name the part before @: chain participants exclude mailbox logins, so a bare name would show the user's own address as a counterparty

## Alternatives
per-service login rule: the part before @ for Yandex and iCloud

## Reason
chain participants are the addresses other than the logins of the user's mailboxes (ADR 0044); full address also signs in on Yandex and iCloud
