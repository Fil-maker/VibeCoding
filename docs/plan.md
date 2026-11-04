# Plan

Version 0.22 · 05.11.2026

Changes in 0.22: task 1.10 «Edit and delete a project» done.

Changes in 0.21: task 1.9 «Mailbox connection hints» done.

Changes in 0.20: task 1.8 «Visual system» done.

Changes in 0.19: task 1.8 «Visual system» also removes the duplicate «Создать проект» on the empty «Проекты» and the old «На главную» links.

Changes in 0.18: task 1.7 «App shell and user path» done.

Changes in 0.17: tasks 1.7 «App shell and user path» and 1.8 «Visual system» prepare stage 1 for the release.

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
| 1.7 | **App shell and user path.** One frame for every signed-in page: a header with the sections and the user's menu; first steps on the start page; a landing page for guests; one look for loading, empty and error states. SPA only, no API changes | FR-48…FR-52, FR-6, FR-17 | A guest who opens «/» sees a landing page that says what the app does in three steps, with «Зарегистрироваться» and «Войти»; any other protected page still sends them to «Вход» and back after sign-in. Every page of a signed-in user has a header with «Проекты», «Переписка», «Почтовые ящики» and «Правила», the current section marked, and the user's name with «Выйти». At 360 px wide the sections fold into a menu button. A new user's start page shows three steps (connect a mailbox, create a project, fill it), each marked done or leading to its page; once all three are done, the start page lists the user's projects. Every list page shows one kind of empty state with a link to the next action, one kind of loading state, and errors in one alert. The keyboard reaches every header item and a «К содержимому» link, focus is visible, and the browser tab title names the page. `just check` and `just test-all` pass. |
| 1.8 | **Visual system.** Light and dark themes that follow the system setting, buttons of three kinds, badges for the placement reason, a project tree that folds, and a phone layout for every page; the duplicate «Создать проект» on the empty «Проекты» and the old «На главную» links inside the app frame go away. Behavior unchanged; technical change (`skip_specs`) | — | The theme follows the system's light or dark setting, and body text has a contrast of at least 4.5:1 in both themes. Buttons come in three kinds (primary, secondary, danger); deleting a mailbox or a rule and refilling a project use the danger kind and still ask for confirmation. The placement reason is a badge: «вручную», «правило» or «движок» with its similarity. In the project tree each counterparty folds and unfolds. Every page reads at 360 px without horizontal scrolling; tables become cards there. No color or pixel size is written outside `tokens.css`. The empty «Проекты» shows «Создать проект» once, in its empty state; with projects listed, the button «Создать проект» stays under the list. No page inside the app frame has «На главную»; the page «Страница не найдена» keeps it. `just check` and `just test-all` pass. |
| 1.9 | **Mailbox connection hints.** The user types an email address; a built-in table of domains picks the mail service, fills the server and port, and shows short steps with a link to the service's official help; a sign-in failure shows the steps for that service. No MX lookup and no external catalogs | FR-53, FR-54, FR-22, FR-26 | On «Почтовые ящики» the connect form starts with «Адрес почты». An address on yandex.ru, mail.ru, gmail.com, icloud.com or demo.test picks its service and fills the server and port. The user can change the service by hand; «Другой» leaves the server open and empty and the port 993, with a hint where to find the server, and an unknown domain, outlook.com and rambler.ru among them, picks «Другой». Under «Настройки сервера» the user can change the server and port and set a login other than the address. Every service except «Демо» and «Другой» shows the steps «включить IMAP» and «создать пароль приложения» and a https link to its official help. Above the form the page says why an app password is needed and that the app only reads the mailbox. A sign-in failure on connecting and «не удалось войти в ящик» in the list show the steps and the link of the mailbox's service; «сервер не отвечает» does not. The answer of GET /api/v1/mailboxes carries error_code and still never the password. Picking the service sends no request to any external service. `just check` and `just test-all` pass. |
| 1.10 | **Edit and delete a project.** The user renames a project and changes its description, which moves no chain, and deletes a project after a confirmation; its chains stay as taken out by hand, its rules go with it, the emails stay | FR-55, FR-56, FR-41, FR-45 | On the page of a project «Изменить» changes its name and description by the checks of creation, and «Проекты», the rules and the chain pages show the new name. Changing the description moves no chain; a filled project then shows «Описание изменено после заполнения: нажмите «Заполнить», чтобы пересобрать проект» until it is filled again. «Удалить проект» asks for confirmation naming how many chains leave the project and how many rules are deleted; on «Удалить» the project is gone from «Проекты» and the user lands there, on «Отмена» nothing changes. After the deletion every chain of the project shows «Вне проектов · убрана вручную» and stays in «Переписка» with all its emails; neither «Заполнить» of another project, a rule nor a mailbox read places it again; only the user does by hand. The rules targeting the project are no longer listed on «Правила». A user editing or deleting another user's project gets «not found» and that project does not change. `just check` and `just test-all` pass. |
