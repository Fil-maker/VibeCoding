# Plan

Version 0.16 · 03.11.2026

Changes in 0.16: task 1.6 «Apply a rule now» done.

Changes in 0.15: task 1.6 «Apply a rule now».

Changes in 0.14: task 1.5 «Rules» done.

Changes in 0.13: task 1.5 «Rules» gets its full «Done when».

Changes in 0.12: task 1.4 «Manual placement and re-sorting» done.

Changes in 0.11: task 1.4 is split; rules go to the new task 1.5 «Rules».

Changes in 0.10: task 1.3 «Projects and the engine» done.

Changes in 0.9: task 1.3 «Projects and the engine» gets FR-32…FR-39.

Changes in 0.8: task 1.2 «Mailboxes and reply chains» done.

Changes in 0.7: tasks 1.2–1.4 of stage 1 «Project trees», the first version shown to the customer.

Changes in 0.6: task 1.1 «Personal accounts» done.

Changes in 0.5: task 1.1 «Personal accounts».

Changes in 0.4: task 0.2 «Sign-in and organization» done.

Changes in 0.3: task 0.2 «Sign-in and organization».

Changes in 0.2: task 0.1 «Application skeleton» done.

Changes in 0.1: task 0.1 «Application skeleton».

## How work runs

- A task is one change: one branch, one OpenSpec change, one journal note.
- `/feature` leads a task from the plan row to `/finish`; `/fix` leads a bug.
- «Done when» is what the user will see, in checkable sentences, each ending with a period.
- FR is «—» until the spec delta is approved.
- Ids are stable: a new task takes the highest id + 1; dropped ids are not reused.

## Tasks

| # | Task | FR | Done when |
|---|---|---|---|

## Done

| # | Task | FR | Done when |
|---|---|---|---|
| 0.1 | **Application skeleton.** FastAPI backend, React SPA and PostgreSQL start together with one command; technical change, no specs (`skip_specs`) | — | `just dev` starts the database, the backend and the SPA. The SPA page shows the backend's health status, in Russian, read through the generated API client. `just check` and `just test-all` pass with the backend and frontend checks included. |
| 0.2 | **Sign-in and organization.** An organization registers itself, its registrant becomes the first administrator, employees join by an emailed invitation; sign-in with email and password, password reset by email, members management; the organization and owner filter for all later data | FR-1…FR-20 | A new organization registers on the page «Регистрация», and its registrant signs in after following the confirmation link from the email caught by Mailpit. The administrator invites an employee by email; the employee accepts the invitation, sets a password and signs in; a used, revoked or expired invitation is refused. A user who forgot the password resets it by the emailed link, and their old sessions stop working. After 5 wrong passwords in 15 minutes sign-in for that email is locked for 15 minutes. The administrator sees the members of the organization, deactivates an employee, who can no longer sign in, and appoints another administrator; the last active administrator cannot be removed. An employee cannot open the administrator's pages or actions, and a user of organization A gets «not found» for data of organization B. When SMTP fails, the invitation is shown as «not sent» and can be sent again. `just check` and `just test-all` pass. |
| 1.1 | **Personal accounts.** Organizations are removed: anyone registers as an individual user with email confirmation; invitations, members, roles, deactivation and the organization filter go away; every piece of data belongs to one user | FR-1…FR-4, FR-6…FR-8, FR-17, FR-20, FR-21; removes FR-9…FR-16, FR-18, FR-19 | A visitor registers on «Регистрация» with a name, email and password, follows the confirmation link from the email caught by Mailpit and lands on the start page with their name and «Выйти», without any organization. The pages «Участники» and invitation acceptance answer «Страница не найдена», and the invitation and members API no longer exists. Users who existed before the migration sign in with their old email and password, each as a separate account, formerly deactivated ones included. A user never gets another user's data: a session token of one user gives only their own profile. Sign-in, lock, sign-out and password reset work as before. `just check` and `just test-all` pass. |
| 1.2 | **Mailboxes and reply chains.** The user connects several mailboxes over IMAP read-only, with the password stored encrypted; Inbox and Sent of the last 12 months are read in the background and on «Обновить»; a local demo mail server holds prepared correspondence; the emails of all mailboxes are collected into reply chains | FR-22…FR-31 | The user connects two mailboxes, and a wrong password is reported. After reading, the user sees the reply chains of all mailboxes and opens one to read its emails; an email present in both mailboxes is shown once; unread emails stay unread in the mailbox. A new email in the mailbox appears after «Обновить» or within 5 minutes. A disconnected mailbox is no longer read, and its emails stay. `just demo-mail` fills the demo mailboxes with prepared correspondence. `just check` and `just test-all` pass. |
| 1.3 | **Projects and the engine.** The user creates a project with a description; a local deterministic engine fills it as a tree project → counterparty → thread and places new chains | FR-32…FR-39 | The user creates a project, presses «Заполнить» and sees the tree. Every placed chain shows why it is there, its similarity and the engine version. Chains the engine is not sure of go to «Неразобранное». New emails take their place in the tree without moving chains already placed. Filling the same project from the same emails again gives the same tree. `just check` and `just test-all` pass. |
| 1.4 | **Manual placement and re-sorting.** The user moves a chain by hand into a project, a thread or «Неразобранное», takes it out of projects for good, and re-sorts a project explicitly | FR-35…FR-37, FR-39…FR-42 | On the page of a chain the user moves it into a thread of any of their projects, into «Неразобранное» or into a new thread they name, and the chain then shows «Вручную». A chain moved by hand stays where the user put it: a new email in it, a mailbox read and «Заполнить» never move it. «Убрать из проекта» takes a chain out of its project, and the engine never places it again by itself. «Заполнить» on a filled project keeps the chains placed by hand and the threads holding them, and lays out the rest again. Every chain in a project tree shows whether it was placed by hand or by the engine. `just check` and `just test-all` pass. |
| 1.5 | **Rules.** The user writes rules by sender address, domain or subject words that place chains into a project and a thread before the engine, on a mailbox read and on «Заполнить» | FR-35…FR-37, FR-39, FR-42…FR-46 | On the page «Правила» the user creates a rule by sender address, domain or subject words with a target project and thread name, and edits or deletes it. A new chain matching a rule goes into its project and thread before the engine compares it, and the thread is created when the project has none of that name. «Заполнить» places the chains matching the project's rules by those rules first and gives the rest to the engine. When two rules match a chain, an address wins over a domain and a domain over subject words. A chain placed by a rule shows «Правило» and the rule. A rule never moves a chain placed by hand or taken out of projects. `just check` and `just test-all` pass. |
| 1.6 | **Apply a rule now.** After a rule is created or edited, the page «Правила» lists the chains it would move and moves them when the user confirms, without «Заполнить» | FR-45…FR-47 | After the user saves a rule on «Правила», the page lists the chains it would move, each with where it is now and where it goes, with «Применить» and «Не сейчас». On «Применить» those chains are in the rule's project and thread and show «Правило» with the rule; on «Не сейчас» nothing moves. A chain in no project, placed by the engine (also in «Неразобранное») or placed by another rule is moved; a chain placed by hand or taken out of projects never is. A chain that a stronger rule wins stays where it is. After an edit, the chains the rule placed before that still match go to its new target, and those that no longer match stay where they are. A thread left empty by the move disappears. A rule that would move nothing says «Подходящих цепочек нет» and moves nothing. `just check` and `just test-all` pass. |
