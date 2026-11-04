# Frontend

Updated 04.11.2026

**Code:** `frontend/src/`, `frontend/index.html`, `frontend/vite.config.ts`, `frontend/package.json`,
`frontend/tsconfig.json`, `frontend/eslint.config.js`, `frontend/.prettierrc.json`, `frontend/.prettierignore`.
The chain page's «Проект» block is `frontend/src/features/projects/ChainPlacement.tsx`.
The tests are `frontend/src/App.*.test.tsx`, the unit tests next to their files (`frontend/src/**/*.test.ts(x)`, such as
`frontend/src/components/Button.test.tsx`, `frontend/src/features/health/HealthStatus.test.tsx` and `frontend/src/styles/tokens.test.ts`) and `frontend/src/test/`.

**Requirements:** the pages and guards carry out [FR-1 … FR-3](../../openspec/specs/organization-registration/spec.md) registration,
[FR-4 … FR-8](../../openspec/specs/sign-in/spec.md) sign-in and password reset,
[FR-17, FR-20 and FR-21](../../openspec/specs/access-boundary/spec.md) the access boundary,
[FR-22, FR-23, FR-24, FR-26 and FR-27](../../openspec/specs/mailboxes/spec.md) the mailbox page,
[FR-53 and FR-54](../../openspec/specs/mailboxes/spec.md) the connect form's service pick and its hints,
[FR-30 and FR-31](../../openspec/specs/reply-chains/spec.md) the correspondence pages,
[FR-32 … FR-34](../../openspec/specs/projects/spec.md) the project pages and
[FR-35 … FR-42](../../openspec/specs/chain-placement/spec.md) the fill button of a project and the «Проект» block of a chain,
[FR-43 … FR-45 and FR-47](../../openspec/specs/placement-rules/spec.md) the rules page and the panel after a saved rule, and [FR-37](../../openspec/specs/chain-placement/spec.md)
the rule explanations of a placement, and [FR-48 … FR-52](../../openspec/specs/app-shell/spec.md) the landing page (FR-48),
the header and sections (FR-49), the start page's first steps (FR-50), the shared page states (FR-51) and the keyboard and
page titles (FR-52). The health page has no requirement:
task 0.1 is a technical change without specs ([ADR 0004](../adr/0004-task-0-1-runs-as-a.md)).

**Design:** [Components and processes](../architecture.md#components-and-processes),
[Repository structure](../architecture.md#repository-structure), [Routes and API](../architecture.md#routes-and-api)
(the SPA route table), [Stack](../tech.md#stack), [Environment variables](../tech.md#environment-variables).

**Related:** [Auth and accounts](auth.md) for the backend side of sign-in, sessions and registration;
[Backend](backend.md); [Mail reading](mail-reading.md) for the backend side of mailboxes and reply chains;
[Projects](projects.md#the-spa) for the project pages in full and [Projects](projects.md) for the backend side.

## Entry and providers

- `frontend/index.html` is the page shell: `lang="ru"`, title `VibeCoding`, an empty `<div id="root">`, and
  the module script `/src/main.tsx`.
- `frontend/src/main.tsx` finds `#root`, throws when it is missing, and renders `<App />` inside `StrictMode`.
  It imports the design tokens (`frontend/src/styles/tokens.css`) once, so every component gets them.
- `frontend/src/App.tsx` is the root component. From outside in it renders `QueryClientProvider`, `BrowserRouter`,
  `AuthProvider` and then `Routes`. See [Routing](#routing).
- `BrowserRouter` runs with `useTransitions={false}`, so navigation commits at once. The reason is in
  [ADR 0080](../adr/0080-browserrouter-runs-with-usetransitions-false-and.md): sign-out must reach «/» before the
  session clears (see [Frames](#frames)).
- `App` takes an optional `queryClient` prop. It defaults to the page's query client, which is created once, at
  module load of `App.tsx`, with `createQueryClient()` (see [Query client](#query-client)). Tests pass their own.

## Routing

- The SPA uses react-router 7 in declarative mode: `BrowserRouter`, `Routes`, `Route`, `Navigate` and `Outlet`
  ([ADR 0015](../adr/0015-spa-routing-with-react-router-7.md)).
- The paths and who sees each page are in [Routes and API](../architecture.md#routes-and-api), under «SPA routes».
  This article covers how `App.tsx` nests them:
  - `RequireGuest` wraps the pages for a signed-out visitor: `/register`, `/sign-in` and `/forgot-password`, all in `GuestLayout`.
  - `RequireUser` wraps `/mailboxes`, `/chains`, `/chains/:id`, `/projects`, `/projects/new`, `/projects/:id` and `/rules`,
    all in `AppLayout`.
  - The pages that take their token from the link (`/confirm-email` and `/reset-password`, in `GuestLayout`), the health page
    (`/health`, with no frame) stay outside the guards.
  - `/` (the landing page or the start page) and the catch-all route stay outside the guards: they sit under `AuthFrame`,
    which picks the frame by the session (see [Frames](#frames)).
- The catch-all route shows `NotFoundPage`. The addresses `/members` and `/invitation` have no route, so they show
  `NotFoundPage` like any unknown path.

## Frames

Each route renders inside one frame, a layout route in `App.tsx`. The frame is the same for every page of its kind;
the page renders its own content inside it (see [Components](#components)).

- `PageFrame` (`frontend/src/features/shell/PageFrame.tsx`) is the frame every page shares. It renders the skip link
  «К содержимому» first, then the header, then the one `<main id="content">` with the page. The skip link moves focus
  to that `<main>` (it has `tabIndex={-1}`) and leaves the URL alone.
- `AppLayout` (`frontend/src/features/shell/AppLayout.tsx`) is the frame of a signed-in user: `PageFrame` with `AppHeader` as its header.
  The routes under `RequireUser` all use it.
- `AppHeader` (`frontend/src/features/shell/AppHeader.tsx`) holds:
  - the brand «VibeCoding», a link to `/`;
  - the section links «Проекты» (`/projects`), «Переписка» (`/chains`), «Почтовые ящики» (`/mailboxes`) and «Правила»
    (`/rules`), in that order, as `NavLink`s in the nav «Разделы»; the open page's section is the current one (`aria-current`);
  - the user's name and «Выйти».

  Below 40rem (`frontend/src/features/shell/AppShell.module.css`, the one media query, since a media query cannot read a token)
  the sections, the name and «Выйти» fold behind the button «Меню», which sets `aria-expanded` and `aria-controls`.
  The menu closes on Escape, when a section is pressed, and when the route changes.
  «Меню» and «Выйти» are `Button`s of the `secondary` kind ([Components](#components)). Their look is the shared button class
  in `ui.module.css`; `AppShell.module.css` keeps only the layout, and its `.toggle` (the «Меню» button) is hidden above 40rem
  and shown below it.
- «Выйти» in the header sends `DELETE /api/v1/auth/sessions/current`. On success it navigates to `/` inside `flushSync`, and only
  then clears the session with `setSession(null)`, so the landing page shows. The reason is in
  [ADR 0080](../adr/0080-browserrouter-runs-with-usetransitions-false-and.md).
- `GuestLayout` (`frontend/src/features/shell/GuestLayout.tsx`) is the frame of a signed-out visitor: `PageFrame` whose header is
  only the brand «VibeCoding», linking to `/`. It wraps `/register`, `/sign-in`, `/forgot-password`, `/confirm-email` and
  `/reset-password`.
- `AuthFrame` (`frontend/src/features/shell/AuthFrame.tsx`) wraps `/` and the catch-all route. While the session is `loading`, or the
  session check failed, it shows `Waiting` (`frontend/src/components/Waiting.tsx`, the tab title plain «VibeCoding»). A
  signed-in user gets `AppLayout`; anyone else gets `GuestLayout`.
- `HealthStatus` at `/health` renders outside every frame.

## Auth state

`frontend/src/features/auth/AuthProvider.tsx` is the one place that knows who is signed in.

- It reads `GET /api/v1/auth/me` through `apiClient` under the query key `['auth', 'me']`, with `retry: false`.
  A 401 answer means signed out. Any other failure is the error state.
- `useAuth()` returns `state` and `setSession`. `state.status` is `loading`, `error`, `signedOut`, or `signedIn`
  with the signed-in `me`. `useAuth()` throws when it is used outside the provider.
- `setSession(me)` records the user that sign-in or email confirmation returned.
  `setSession(null)` is the sign-out. On sign-out it removes every cached query except the auth one, so nothing
  of the previous user stays in the cache.
- `useRefreshSession()` returns a function that re-reads `GET /api/v1/auth/me`. No page calls it at present.
- The SPA never reads the session cookie `vc_session`: it is HttpOnly ([ADR 0012](../adr/0012-sessions-are-stored-server-side-in.md)),
  so the SPA learns who is signed in only from `/auth/me`. The server side is in
  [Sign-in, the lock and sessions](auth.md#sign-in-the-lock-and-sessions).

## Route guards

`frontend/src/features/auth/guards.tsx` holds the two guards. While the auth state is `loading`, `RequireUser` and
`RequireGuest` show the waiting panel with the title `VibeCoding` and the text `Загрузка…`. In the `error` state they show
the same panel with `Сервер не отвечает` as an alert.

- `RequireUser`: a signed-out visitor goes to `/sign-in?next=…`, where `next` is the URL-encoded path and query they
  asked for. A signed-in user gets the nested routes.
- `RequireGuest`: a signed-in user goes to `next`, or to `/` when there is none. `safeNext` accepts only a path of
  this site: it must start with `/` and not with `//`.

## Pages

Each page is a function component in its feature folder; `NotFoundPage` is the exception and lives in `frontend/src/components/`. Its texts are Russian and written in the component.
Every page is a `Panel` whose `title` is its `h1`, except the landing page (its own `<section>` with its heading) and the
health page (its own `<section>`, see [Health feature](#health-feature)).

| Page (title) | File | What it does |
|---|---|---|
| «Регистрация» | `frontend/src/features/auth/RegisterPage.tsx` | Fields «Имя», «Email» and «Пароль»; posts name, email and password. Shows the confirmation text with the email, or the mail-failure text when the mail did not go out. The link in the email signs the registrant in. |
| «Подтверждение email» | `frontend/src/features/auth/ConfirmEmailPage.tsx` | Posts the token from the link once, on arrival, then calls `setSession` and goes to `/`. Without a token it shows `Ссылка недействительна или устарела`. |
| «Вход» | `frontend/src/features/auth/SignInPage.tsx` | Posts email and password, then `setSession`; `RequireGuest` takes the user on. Links «Забыли пароль?» and «Регистрация». |
| «Восстановление пароля» | `frontend/src/features/auth/ForgotPasswordPage.tsx` | Posts the email. The answer is the same text for every email. |
| «Новый пароль» | `frontend/src/features/auth/ResetPasswordPage.tsx` | Takes the token from the link, posts it with the new password and shows `Пароль изменён. Теперь можно войти` with a link to «Вход». Without a token it shows the invalid-link text. |
| «Первые шаги» (`/`, signed in) | `frontend/src/features/home/StartPage.tsx` | The three steps «Подключите почтовый ящик», «Создайте проект» and «Заполните проект»: a done step shows its label and «Готово», a step not done links to its page (the third step to the first project not yet filled, or to `/projects` when none is left). It reads the mailboxes and projects under the keys `MAILBOXES_KEY` and `PROJECTS_KEY`, and it opens «Проекты» once all three are done. The tab title is plain «VibeCoding». See [Frames](#frames) for the header. |
| The landing page (`/`, guest) | `frontend/src/features/home/LandingPage.tsx` | The heading «Переписка по проектам — в одном дереве», three steps, and the links «Зарегистрироваться» (`/register`) and «Войти» (`/sign-in`). It reads no user data. `HomeRoute.tsx` picks the landing page or the start page by the session. |
| «Почтовые ящики» | `frontend/src/features/mailboxes/MailboxesPage.tsx` | The connected mailboxes, their reading status, «Обновить», «Отключить», and the connect form. See [Mailboxes feature](#mailboxes-feature). |
| «Переписка» | `frontend/src/features/correspondence/ChainsPage.tsx` | The reply chains, the latest first, a page at a time. See [Correspondence feature](#correspondence-feature). |
| The chain's subject (`/chains/:id`) | `frontend/src/features/correspondence/ChainPage.tsx` | One reply chain: the block «Проект» (where the chain is, «Перенести», «Убрать из проекта»), then its emails oldest first, each as plain text. See [Correspondence feature](#correspondence-feature) and [Projects feature](#projects-feature). |
| «Проекты» (`/projects`) | `frontend/src/features/projects/ProjectsPage.tsx` | The user's projects by name, with their chain counts. With projects listed, the button «Создать проект» sits under the list; with none, the empty state shows the link instead (see [Page states](#pages)). See [Projects feature](#projects-feature). |
| «Новый проект» (`/projects/new`) | `frontend/src/features/projects/NewProjectPage.tsx` | Fields «Название» and «Описание»; «Создать» opens the new project. See [Projects feature](#projects-feature). |
| «Правила» (`/rules`) | `frontend/src/features/projects/RulesPage.tsx` | The form of a rule, the user's rules in the order they win, with «Изменить» and «Удалить»; after a rule is saved, the panel «Применить правило сейчас?» (`RuleApplyPanel.tsx`). See [Rules feature](#rules-feature). |
| The project's name (`/projects/:id`) | `frontend/src/features/projects/ProjectPage.tsx` | One project: its description, «Заполнить» with the rebuild question, and the tree of its chains. See [Projects feature](#projects-feature). |
| «Состояние сервиса» | `frontend/src/features/health/HealthStatus.tsx` | The health page; see [Health feature](#health-feature). |
| «Страница не найдена» | `frontend/src/components/NotFoundPage.tsx` | See [Components](#components). |

Forms carry no client-side rules. Each `<form>` has `noValidate`, so the server decides; the per-field messages of
the answer show under their fields (see [Errors and messages](#errors-and-messages)).

**Page states.** The list and detail pages use the shared states of [Components](#components): `Loading` while the first
answer is pending, `EmptyState` for an empty list (with its link to the next action), and `LoadError` for a failed load,
which shows the error in one alert with «Повторить». The texts of each page:

- «Переписка» (`/chains`): with no chain, `Писем пока нет: подключите почтовый ящик` and the link «Подключить ящик» (`/mailboxes`).
- «Почтовые ящики»: with no mailbox, `Ящики ещё не подключены` as a plain paragraph, with no link.
- «Проекты» (`/projects`): with no project, `Проектов пока нет: создайте первый` and the link «Создать проект» (`/projects/new`).
  It is the only «Создать проект» on the empty page; with projects listed, the button sits under the list instead.
- «Правила» (`/rules`): with no project, `Сначала создайте проект` and the link «Создать проект» (`/projects/new`), with no form;
  with no rule, `Правил пока нет` as a plain paragraph.
- The chain's page and the project's page: while loading, a «Переписка» or «Проект» panel with `Загрузка…`; a failed load shows
  the alert with «Повторить»; a 404 shows `NotFoundPage`.
- The start page: while the mailboxes or the projects load, `Загрузка…` with no panel title; a failed load shows the panel
  «Первые шаги» with the alert and «Повторить».

## Mailboxes feature

The feature is in `frontend/src/features/mailboxes/`. `MailboxesPage.tsx` is the page «Почтовые ящики»: the list, the read-only
note and the connect form. `MailboxRow.tsx` is one row of the list, `ConnectForm.tsx` is the connect form, `ServiceSteps.tsx` is the
block «Как подключить <service>», `mailServices.ts` is the table of mail services with the match of an address to one of them, and
`mailboxesKey.ts` is the query key `MAILBOXES_KEY`, which the start page reads too. `mailServices.test.ts` is the unit test of the table.
The server side is in [Mail reading](mail-reading.md).

- The page is a `Panel` titled «Почтовые ящики». It reads `GET /api/v1/mailboxes` under the
  query key `['mailboxes']` (`MAILBOXES_KEY`). While the query loads it shows `Загрузка…`; with no mailbox it shows `Ящики ещё не подключены`.
- The list is a table with the login, the server, the status and the actions of each mailbox. The page never shows a password.
- **The note.** Under the list and above the connect form the page shows `Приложение только читает письма: не отправляет, не удаляет и не помечает их прочитанными. Для входа нужен пароль приложения — отдельный пароль для почтовых программ, который можно отозвать, не меняя основной.`
- **Status text.** The text comes from `statusText` in `MailboxRow.tsx`; the values are exactly:

  | `status` | Text |
  |---|---|
  | `pending` | `Ожидает чтения` |
  | `reading` | `Читается…` |
  | `read` | `Прочитан` when `last_read_at` is null; `Прочитан ` and the local date and time of `last_read_at` otherwise |
  | `failed` | `Ошибка: ` and the mailbox's `error` text |

- **Polling.** The list query refetches every 5 seconds (`POLL_INTERVAL_MS = 5000`) only while some mailbox is `pending` or
  `reading`. When every mailbox is `read` or `failed`, it does not poll.
- **«Обновить».** It calls `POST /api/v1/mailboxes/{mailbox_id}/refresh` for that row only. The button is disabled while the
  request runs; on success the list is invalidated. The reading itself happens at the next tick of the server's reading loop.
- **«Отключить» with a confirmation.** The first click does not send anything. It replaces the row's buttons with the text
  `Отключить ящик {login}? Прочитанные письма останутся.` and two buttons: «Отключить» (the `danger` kind; sends `DELETE /api/v1/mailboxes/{mailbox_id}`;
  the button is disabled while the request runs) and «Отмена» (`secondary`; returns the row's buttons, sends nothing). Whatever the answer,
  the confirmation closes. On success the list is invalidated and the mailbox disappears. A failure shows its message in the row.
- **«Как исправить».** `MailboxRow.tsx` shows the button «Как исправить» on a row only when its `error_code` is `sign_in_failed`
  and its `server` is the server of a service in the table that has steps (`serviceForServer`). The demo server `greenmail` and an
  unknown server get no button, and neither do the codes `unreachable` and `read_failed`. A click shows the block
  «Как подключить <service>» under the row's status; nothing closes it again.
- **The connect form.** The heading «Подключить ящик» sits above `ConnectForm.tsx`. Its fields come in this order:
  1. «Адрес почты». It is also the login until the user changes the login. Typing it picks the service by its domain.
  2. «Почтовый сервис»: a select with «Яндекс Почта», «Mail.ru», «Gmail», «iCloud», «Демо» and «Другой», in the table's order.
  3. For «Другой», once an address is typed or the service is picked by hand, the text `Этот почтовый сервис нам незнаком. Адрес сервера IMAP и порт есть в справке вашей почты или у администратора домена.`
  4. The block «Как подключить <service>» of the picked service, when it has steps.
  5. The disclosure «Настройки сервера» with «Сервер IMAP», «Порт» (`993` at first) and «Логин». It opens by itself for «Другой»
     while the hint shows, and the user can open and close it. A connect answer with a message for the server, for the port or,
     after a hand edit, for the login opens it.
  6. «Пароль приложения» (a password field) and the button «Подключить».

  The first state is the service «Другой», an empty server, the port `993` and an empty login. Typing an address sets the service,
  the server and the port from its domain, and the login to the full address, for every service ([ADR 0093](../adr/0093-the-login-defaults-to-the-full.md)).
  A server or a port the user typed by hand stays when the address changes; a login the user typed stays too. A service picked
  by hand fills the server and the port and never the login; it stays while the domain of the address does not change, and a
  new domain picks the service again.

  Submitting with an empty address sends no request. It names every empty or invalid field at once: «Укажите адрес почты»,
  «Укажите сервер IMAP», «Порт должен быть от 1 до 65535» and «Укажите пароль приложения». Otherwise the form posts
  `POST /api/v1/mailboxes` with `server`, `port` (a number), `login` and `password`. The form has `noValidate`. The server's
  per-field messages show under their fields; a login message shows under «Адрес почты» while the login is not edited by hand.
  When no field has a message, the answer's message shows above the form (for example «Этот ящик уже подключён» for
  `mailbox_exists`). On success the form returns to its first state and the list is invalidated.
- **The service table.** `mailServices.ts` holds `MAIL_SERVICES`, the app's own list of mail services (`MailService`: `id`, `name`,
  `howToTitle`, `server`, `port`, `steps` and `help`). It is static data, so matching an address sends no request.

  | Service | Server | Port | Domains | Steps and link |
  |---|---|---|---|---|
  | Яндекс Почта | `imap.yandex.ru` | 993 | `yandex.ru`, `ya.ru`, `yandex.com` | steps; «Справка Яндекс Почты» |
  | Mail.ru | `imap.mail.ru` | 993 | `mail.ru`, `inbox.ru`, `list.ru`, `bk.ru`, `internet.ru` | steps; «Справка Mail.ru» |
  | Gmail | `imap.gmail.com` | 993 | `gmail.com`, `googlemail.com` | steps; «Справка Google» |
  | iCloud | `imap.mail.me.com` | 993 | `icloud.com`, `me.com`, `mac.com` | steps; «Справка Apple» |
  | Демо | `greenmail` | 3143 | `demo.test` | none |
  | Другой | empty | 993 | any other domain | none |

  - `domainOfAddress` takes the part after the last «@», trimmed and lowercased. `serviceForAddress` looks it up in the domain
    list `DOMAINS`; no match is «Другой». Case and spaces do not matter.
  - `serviceForServer` returns the service whose server equals the given server, trimmed and lowercased; no match gives null.
  - Outlook (`outlook.com`, `hotmail.com`, `live.com`) and Rambler (`rambler.ru`) are not in the table, so they pick «Другой»
    ([ADR 0091](../adr/0091-outlook-is-left-out-of-the.md), [ADR 0092](../adr/0092-rambler-is-left-out-of-the.md)). The reason for the
    demo entry is in [ADR 0090](../adr/0090-the-service-table-holds-for-demo.md).
- **«Как подключить <service>».** `ServiceSteps.tsx` renders a region named by the service's title (`howToTitle`, for example
  «Как подключить Яндекс Почту»), with the steps as an ordered list and the official help link. The link opens in a new tab with
  `rel="noopener noreferrer"` and carries no part of the address. Nothing renders for «Демо» and «Другой».

## Correspondence feature

The files are `frontend/src/features/correspondence/`: `ChainsPage.tsx` (the list), `ChainPage.tsx` (one chain),
`ChainPage.module.css` (its styles) and `format.ts` (the date, count and address texts of both pages). The server side is in
[Mail reading](mail-reading.md#reading-a-reply-chain).

- **The list (`/chains`).** The page «Переписка» reads `GET /api/v1/reply-chains` as an infinite query under the key
  `['reply-chains']`. The SPA sends no `limit`, so the server's default page size applies. Each row shows the subject as a link to
  `/chains/{id}`, the participants (`formatAddresses`), the email count (`emailCountLabel`, for example «1 письмо», «2 письма»,
  «5 писем») and the date of the latest email (`formatDate`, date only). With no chain it shows `Писем пока нет: подключите почтовый ящик` with the link «Подключить ящик» (see [Pages](#pages)).
  The button «Показать ещё» loads the next page with the `cursor` of the last answer. It is disabled while that page loads, and it
  is not shown when the last answer has no `next_cursor`.
- **One chain (`/chains/:id`).** `ChainPage` reads `GET /api/v1/reply-chains/{chain_id}` under the key `['reply-chains', id]`.
  The page title is the chain's subject, and the link «К переписке» goes back to `/chains`. It retries once on an error, except a
  404, which shows `NotFoundPage` (`Страница не найдена`): another user's chain and an unknown id look the same. While loading, and
  on any other error, the page is a «Переписка» panel with `Загрузка…` or the error alert with «Повторить». Under the link «К переписке»
  the page shows the block «Проект» (`ChainPlacement`, see [Projects feature](#projects-feature)), then the emails.
- **Each email** is an `<article>` in the order of the answer, oldest first: `Тема:` with the email's subject, `От:` with the sender, `Кому:` with the recipients,
  `Копия:` only when there are copies, the sent date and time (`formatDateTime`), the text, and `Вложения: ` with the attachment
  names joined by `, ` only when there are attachments. The server keeps only the file names of attachments, so the page shows names only
  ([Mail reading](mail-reading.md#html-to-text)).
- **The text is plain text.** The text is rendered as a React child in an element with the class `.text`, which sets
  `white-space: pre-wrap` (`ChainPage.module.css`). The SPA never sets HTML from it: no `dangerouslySetInnerHTML`, and the ESLint
  rule `react/no-danger` is an error. Markup in an email shows as the characters it is.
- **Formatting (`format.ts`).** Dates use `Intl.DateTimeFormat('ru-RU')` in the user's local time: `formatDate` gives `29.10.2026`,
  `formatDateTime` gives `29.10.2026, 14:05`. `emailCountLabel` picks the Russian plural with `Intl.PluralRules('ru')`.
  `formatAddress` gives `Имя <адрес>` when the name is known and the bare address otherwise. The `Address` type is taken from the
  generated schema.

## Projects feature

The files are `frontend/src/features/projects/`: `ProjectsPage.tsx` (the list, and `PROJECTS_KEY`, the query key `['projects']`
that the other two files invalidate), `NewProjectPage.tsx` (the form), `ProjectPage.tsx` (one project, its fill and its tree),
`ProjectPage.module.css` (the tree's indents, the description's line breaks, the muted counterparty address and the heading inside a
  folding summary), `ChainPlacement.tsx` (the «Проект» block of a chain page, see below), `PlacementBadge.tsx` with `PlacementBadge.module.css`
  (the badge of a placement, see below), `format.ts`, `RulesPage.tsx` and `RuleApplyPanel.tsx` (the page «Правила» and its panel,
  see [Rules feature](#rules-feature)).
The server side is in [Projects](projects.md). The pages, their routes and their texts are described in
[The SPA](projects.md#the-spa) of that article; this section only says where things live.

- **Texts.** Each page writes its Russian texts in its component. The two texts of the project page's empty tree
  are constants at the top of `ProjectPage.tsx`, next to `REFILL_QUESTION` and `NO_COUNTERPARTY_TITLE`.
- **Formatters (`format.ts`).** `chainCountLabel` and `unassignedCountLabel` pick the Russian plural with `Intl.PluralRules('ru')`,
  as `emailCountLabel` does. `placementLabel(placement)` gives `Вручную` for a placement by hand, `Движок text-1 · сходство 43%`
  for an engine one (the similarity (0–1) is shown in whole percent), and for a rule placement the rule's explanation:
  `Правило · адрес s.petrov@stroymaster.example` (condition `address`), `Правило · домен techsnab.example` (`domain`), and
  `Правило · слова темы «акт работ»` (`subject`; the words go in «»).
- **The badge (`PlacementBadge.tsx`).** `PlacementBadge({ placement })` shows the exact text of `placementLabel(placement)` in a
  `<span>` with `data-kind` set to `manual`, `rule` or `engine`. The colors come from the `--color-badge-<kind>-*` tokens in
  `PlacementBadge.module.css`; the color only repeats the text. It is used in two places: each chain row of the project tree
  (and the chains of «Неразобранное») and the «Проект» block of a chain page. `PlacementBadge.test.tsx` checks the three labels
  and their `data-kind`.
- **The tree (`ProjectPage.tsx`).** Each counterparty is a `<details open>` with a `<summary>`, whose heading is the counterparty's
  name and address (or «Без контрагента»). Each thread of it is a `<div>` with its heading and its chain rows, not a folding block.
  «Неразобранное» is a `<details open>` of the same kind, and it appears only when some chain is unassigned. Every counterparty and
  «Неразобранное» is open when the page loads; the mouse and the keyboard fold and unfold each one (the native `<details>` behavior).
- **The «Проект» block (`ChainPlacement.tsx`).** `ChainPage` renders `ChainPlacement({ chainId })`. It reads
  `GET /api/v1/placements/{chain_id}` under the key `['placements', id]`. The text is `<project> → <thread or Неразобранное> · <placement>`,
  with the project name as a link to `/projects/{id}`; `Вне проектов` when the chain is in no project, and `Вне проектов · убрана вручную`
  when it was taken out by hand. The button «Убрать из проекта» shows only for a placed chain; it sends
  `DELETE /api/v1/placements/{chain_id}`. The form «Перенести» (a heading of the same text) has:
  - the select «Проект», with the projects of `GET /api/v1/projects`; it starts at the chain's project, or at the first project when the
    chain is in none;
  - the select «Ветка», with «Неразобранное» (empty value), the threads of the chosen project from
    `GET /api/v1/projects/{project_id}/threads` (key `['projects', project, 'threads']`) and «Новая ветка…». It starts at the chain's own
    thread while its own project is selected, and resets to «Неразобранное» when another project is picked;
  - the field «Название ветки», shown only for «Новая ветка…».

  The submit button «Перенести» sends `PUT /api/v1/placements/{chain_id}` with a `PlacementMove`. A failure with field messages
  (`thread_id`, `new_thread_name`) shows them under their fields, and the alert stays empty; a failure with no field messages
  shows in an alert (`ChainPlacement.tsx`: `errors.size > 0 ? null : move.error`). On success the location is set in the cache and the
  projects query is invalidated, so the tree shows the move.
- **The fill confirmation.** «Заполнить» on a project with any chain in its tree first shows the question `Пересобрать проект?
  Движок разложит его переписку заново` with the buttons «Пересобрать» (the `danger` kind) and «Отмена» (`secondary`); «Отмена» sends
  nothing. «Заполнить» is `primary`. A project with no chain fills at once. While the fill runs the button reads «Заполняется…» and is disabled. On success the page's query data
  is replaced with the answer, and the projects list is invalidated.
- **The header** links to `/projects` as «Проекты», beside «Переписка», «Почтовые ящики» and «Правила» ([Frames](#frames)).
  The start page's third step links to the first project not yet filled (`StartPage.tsx`).
- **The form (`NewProjectPage.tsx`).** It is a `FormField` pair: «Название» (a text field) and «Описание» (`multiline`, see
  [Components](#components)). Its server field messages show under the fields, and the form has `noValidate`.
- **Query keys.** The project page reads under `['projects', id]`, a child of `['projects']`, so invalidating the list also
  refetches an open project.

## Rules feature

The page «Правила» (`/rules`) is `frontend/src/features/projects/RulesPage.tsx`, with `RuleForm` (the form, for a new
rule or for an edit in place) and `RuleLine` (one listed rule, with its edit and delete). The panel «Применить правило сейчас?»
is `RuleApplyPanel.tsx`, in the same folder. The server side is in [Rules](rules.md),
and the route is in [Routes and API](../architecture.md#routes-and-api). The page reads the projects too, so the form can
name the project of a rule. Its query keys are `RULES_KEY` (`['rules']`) and `PROJECTS_KEY` (`['projects']`, see
[Projects feature](#projects-feature)).

- **The page.** A `Panel` titled «Правила», wide, with no «На главную» link ([ADR 0081](../adr/0081-fold-the-removal-of-the-duplicate.md)).
  Both queries show `Загрузка…` while they load,
  and a failed query shows its message in an alert with «Повторить».
- **No project.** With no project the page shows `Сначала создайте проект` with the link «Создать проект» to `/projects/new`, and no form.
- **The form.** Fields «Условие» (a select: «Адрес отправителя», «Домен», «Слова темы»; it starts at «Адрес отправителя»),
  «Значение» (a `FormField`), «Проект» (a select that starts at «Выберите проект», then the user's projects) and «Ветка» (a text
  field with the placeholder «Неразобранное»). The form has `noValidate`. Its button is «Создать правило» (`primary`); the field messages of
  `condition`, `value`, `project_id` and `thread_name` show under their fields, and any other error shows in an alert above them, only
  when the answer has no field errors (`ErrorAlert error={errors.size > 0 ? null : save.error}`, `RulesPage.tsx`).
  After a created rule the fields are empty again.
- **The list.** Each rule is one item of a list, in the order of the answer (the order the rules win). The item reads the condition's
  title, the value, the project's name and the thread's name, joined as `Адрес отправителя: s.petrov@stroymaster.example → Ремонт офиса → Смета`;
  a rule with no thread name shows `Неразобранное` at the end. The titles are «Адрес отправителя», «Домен» and «Слова темы».
  With no rule the page shows `Правил пока нет`.
- **Edit in place.** «Изменить» (`secondary`) replaces the item with the form filled from the rule, with «Сохранить» (`primary`)
  and «Отмена» (`secondary`). «Сохранить»
  sends `PUT /api/v1/rules/{rule_id}`, invalidates the list and returns to the item; a failure shows its messages in that form.
  «Отмена» returns to the item and sends nothing.
- **Delete with a confirmation.** «Удалить» (`secondary`) does not send anything at first. It replaces the item's buttons with the question
  `Удалить правило? Цепочки, уже размещённые им, останутся на месте` and two buttons: «Удалить» (the `danger` kind; sends
  `DELETE /api/v1/rules/{rule_id}`; disabled while it runs) and «Отмена» (`secondary`; returns the buttons, sends nothing). On success the
  list is invalidated and the rule disappears. A failure shows in the item.
- **Create.** The form sends `POST /api/v1/rules` with `condition`, `value`, `project_id` and `thread_name`, read from the form
  fields with `formValue`. The server's `rule_exists` answer («Такое правило уже есть») and `too_many_rules` answer («Правил не может
  быть больше 200») show in the form, as the server's message.
- **The panel «Применить правило сейчас?» (`RuleApplyPanel.tsx`).** After a created rule («Создать правило») and after a saved
  edit («Сохранить»), `RulesPage` shows the panel above the list for that rule. One panel is open at a time; a new offer replaces
  it. On mount the panel reads `GET /api/v1/placements/by-rule/{rule_id}` under the key `['rule-moves', ruleId]`, which is not kept
  in the cache (`gcTime: 0`). Each listed chain reads `<тема>: <откуда> → <проект> → <ветка или Неразобранное>`; `<откуда>` is
  `Вне проектов` for a chain in no project, and otherwise the chain's project and thread (`Неразобранное` for no thread).
  - «Применить» sends `POST /api/v1/placements/by-rule/{rule_id}` with the `chain_ids` of the listed chains, in the list's order.
    Both buttons are disabled while that request runs. On success the panel shows `Перемещено цепочек: N` with N from the answer, and
    «Понятно»; the projects query is invalidated.
  - «Применить» is `primary`; «Не сейчас» and «Понятно» are `secondary`.
  - «Не сейчас» closes the panel and sends nothing.
  - With no chain to move the panel shows `Подходящих цепочек нет` and «Понятно» (no «Применить»); «Понятно» closes the panel.
  - A failed request shows its error in an alert (`ErrorAlert`). When the list request fails, the panel shows only that alert and has
    no button (`RuleApplyPanel.tsx`, the two `ErrorAlert` lines above the list), so it stays on the page until the next offer or a reload.
  - The texts `UNASSIGNED_TITLE`, `NO_PROJECT_TITLE`, `APPLY_QUESTION` and `NO_MOVES_MESSAGE` are constants at the top of
    `RuleApplyPanel.tsx`; the buttons and the result line are written in its JSX.

  Which chains move and how a move is applied are in [Applying a rule now](projects.md#applying-a-rule-now); this section says
  only what the page shows.

## API client

Server data reaches the SPA only through the generated client; components never call `fetch` directly.

- `frontend/src/api/client.ts` exports `apiClient`, an `openapi-fetch` client typed by `paths` from
  `frontend/src/api/generated/schema.ts`. Its `baseUrl` is `window.location.origin`, so requests go to the page's
  own origin; in development the Vite dev server forwards `/api` (see [Dev server](#dev-server)).
- The `fetch` option calls `globalThis.fetch` on each call. The code comment in `client.ts` gives the reason:
  tests can replace the global `fetch`.
- A call looks like `apiClient.GET('/api/v1/health')`. It returns `{ data, error }`; `data` is undefined on a
  non-2xx answer. Wrap the call in `unwrap(...)` to get the data or throw an `ApiError`; `unwrapEmpty(...)` does the
  same for answers without a body (202, 204). A network failure throws from `fetch`.
- Schema types come from `components['schemas'][...]`, for example `Me` in `AuthProvider.tsx` and `HealthStatus`
  in `frontend/src/features/health/useHealth.ts`, `Mailbox` in `frontend/src/features/mailboxes/MailboxRow.tsx`, `MailboxConnect` in `frontend/src/features/mailboxes/ConnectForm.tsx`, and `EmailView`
  and `Address` in the correspondence files. The project files use `ProjectCreate`, `ProjectTree` and `PlacedChain`; the «Проект»
  block uses `ChainLocation` and `PlacementMove`; the rules page uses `Rule`, `RuleInput` and `RuleCondition`, and the panel «Применить правило сейчас?» uses `RuleMove`.

### How the client is regenerated

The schema is the contract; the client is generated from it and committed. Nobody edits the generated files.

1. The backend builds its OpenAPI schema. `backend/app/openapi.py` prints it as JSON (see
   [OpenAPI export](backend.md#openapi-export)).
2. `just api-client` runs `scripts/api_client.py generate`. It writes the schema to
   `frontend/src/api/openapi.json`, then runs `openapi-typescript` on it through `pnpm --dir frontend exec` and
   writes `frontend/src/api/generated/schema.ts`.
3. Both files are committed. Their headers say they are generated; do not edit them by hand.
4. `just check` runs `frontend-api-client`: `scripts/api_client.py check` regenerates both files into a temporary
   directory and fails when the committed files differ. It then prints a stale message that names the files and
   tells the developer to run `just api-client` and commit the result. The check leaves the repository untouched.

After a route changes in the backend, run `just api-client`, commit the two files with the change, and use the
new paths through `apiClient`. `frontend/.prettierignore` skips `frontend/src/api/generated` and `frontend/src/api/openapi.json`;
`eslint.config.js` skips `src/api/generated`. The generated code is therefore neither formatted nor linted.

## Errors and messages

- `ApiError` (`frontend/src/api/request.ts`) carries `code`, `status`, `fields` and the Russian `message`. It is built
  from the error body `{"error": {"code", "message", "fields"}}`; `fields` is optional and maps a field name to its
  message. An answer without that shape, or no answer, becomes an `ApiError` with the code `unknown` and the text
  `Сервер не отвечает`.
- `errorMessage(error)` gives the message to show, `fieldErrors(error)` gives the per-field messages by name, and
  `isNotSignedIn(error)` tells a refusal for a missing or ended session (code `not_signed_in`).
- `ErrorAlert` shows `errorMessage` in an alert and renders nothing without an error. `FormField`'s `error` prop
  shows one field's message under its input and sets `aria-invalid` and `aria-describedby`.
- `frontend/src/messages.ts` holds the texts the server does not send. Every other text on an error comes from the
  server's `message`.

| Constant | Text |
|---|---|
| `SERVER_UNAVAILABLE_MESSAGE` | `Сервер не отвечает` |
| `LOADING_MESSAGE` | `Загрузка…` |
| `INVALID_LINK_MESSAGE` | `Ссылка недействительна или устарела` |
| `REGISTRATION_MAIL_FAILED_MESSAGE` | `Не удалось отправить письмо. Попробуйте зарегистрироваться ещё раз позже` |
| `PASSWORD_RESET_REQUESTED_MESSAGE` | `Если такой email зарегистрирован, мы отправили на него ссылку для сброса пароля` |
| `PASSWORD_CHANGED_MESSAGE` | `Пароль изменён. Теперь можно войти` |
| `NOT_FOUND_TITLE` | `Страница не найдена` |
| `confirmationSentMessage(email)` | `Мы отправили письмо со ссылкой для подтверждения на {email}` |

## Query client

- `frontend/src/api/queryClient.ts` exports `createQueryClient()`, which returns a TanStack Query `QueryClient`
  with one retry for queries (`QUERY_RETRIES = 1`). The code comment in `queryClient.ts` gives the reason: a missing
  backend is reported within seconds instead of after the library's default backoff.
- The auth query sets `retry: false` itself.
- Queries are wrapped in one hook per feature. `useHealth()` is in its own file, `frontend/src/features/health/useHealth.ts`.
  Components use the hook, not the client.

## Components

`frontend/src/components/` holds the shared pieces. Each one takes its look from `ui.module.css`.

- `Button` (`Button.tsx`) is the one button of the SPA. It takes the native `<button>` props, except `type`, and adds
  `kind`: `primary`, `secondary` or `danger`, with `secondary` by default. `type` is narrowed to `'button'`, `'submit'`
  or `'reset'` and defaults to `"button"`, so a submit button passes `type="submit"`. The kind is written to the element
  as `data-kind`, and the class follows it: `primary` (the main action of a form or panel; most are submit buttons, while
  «Заполнить» on a project and «Применить» in the rule panel are `type="button"`), `danger` (the confirming button of a
  removal) and `secondary` (no extra class). The header's «Меню» and «Выйти» are `secondary`. The `danger` confirmations are «Отключить» of a
  mailbox, «Удалить» of a rule and «Пересобрать» of a project; each appears only after the first press, and «Отмена»
  keeps everything. The features' sections describe those flows.
- The source guard: `frontend/src/styles/noLiterals.test.ts` fails on a raw `<button` in a component source (a `.tsx` file
  that is not a test or a file of the test-helper folder) other than `Button.tsx`, so a component's button is a `Button`. The button's look is in `ui.module.css` (see below).
- `Panel` is the page card: a `<section>` with the title as its only `<h1>`. The frame supplies the one `<main>` around it
  (see [Frames](#frames)). `Panel` calls `usePageTitle` (see below): the tab title is `<title> — VibeCoding` by default. The
  optional `tabTitle` prop overrides it, and `tabTitle={null}` gives the plain `VibeCoding` (the start page and `Waiting`
  use it). `wide` widens it to `--size-wide-content-width`.
- `usePageTitle(title)` (`usePageTitle.ts`) sets `document.title` in an effect: `<title> — VibeCoding`, or `VibeCoding` for
  `null`. `LandingPage` calls it directly with `null`, since it has no `Panel`.
- `Loading` is the shared loading state: the text «Загрузка…» in a `role="status"` paragraph.
- `EmptyState` is the shared state of an empty list: its `message`, and an optional `action` (`{ to, label }`), which
  renders as a link after the message.
- `LoadError` is the shared state of a failed load: with a non-null `error`, one `role="alert"` block that shows the
  error's text (`errorMessage`) and the button «Повторить», which calls `onRetry`. A page passes the query's `refetch`.
  With no error it renders nothing. The button is a `Button` of the default `secondary` kind (no kind is passed).
- `Waiting` (`Waiting.tsx`) is the page for a session that is still loading or a server that does not answer: a `Panel`
  titled `VibeCoding` with the tab title plain `VibeCoding`. It shows «Загрузка…», or with `failed` the alert
  «Сервер не отвечает». `RequireUser`, `RequireGuest` and `AuthFrame` use it.
- `FormField` is a labelled input (`type` `text`, `email` or `password`). It takes an optional `defaultValue`, which the
  input shows at first (the rules form uses it for a rule's values). It is uncontrolled: the form reads the values
  from `FormData`. Its label and its message are linked through `useId`.
- `multiline` renders a `<textarea>` with five rows instead of the input (the project description uses it). The `type` prop
  does not apply then. The textarea takes the same `input` look, with `textarea` (vertical resize only).
- `ErrorAlert` is the `role="alert"` paragraph that shows a request's error.
- `NotFoundPage` is a `Panel` titled `Страница не найдена` with the link «На главную» to `/`.
- `formData.ts` exports `formValue(data, name)`, which reads a text field of a submitted form; a missing field counts
  as empty.
- `ui.module.css` holds the shared classes: `panel`, `wide`, `heading`, `subheading`, `form`, `field`, `input`,
  `textarea`, `button`, `primary`, `dangerButton`, `links`, `error`, `notice`, `table` and `actions`. They use only tokens.
  The button classes are `.button` (the base: a border, the surface background, the text color, a pointer cursor),
  `.primary` and `.dangerButton` (the colors of the `--color-button-primary-*` and `--color-button-danger-*` tokens),
  and `.button:focus-visible` (the focus outline `--color-focus`, `--size-focus-width`, `--size-focus-offset`).
  A disabled `.button` is dimmed with `opacity` and keeps the default cursor.
  Below 40rem the file's one media query (the literal `40rem`, since a media query cannot read a token) removes the
  side margins and the side borders of `.panel` and shows each `.table` row as a block card, with the table's cells
  as blocks inside it.

## Link tokens

Email confirmation and password reset links carry their token in the URL fragment: `#token=…`.

- `frontend/src/urlToken.ts` exports `readFragmentToken(hash)`, which returns the token or `null` when it is missing or empty.
  The code comment in `urlToken.ts` gives the reason: a fragment never reaches server logs.
- The SPA sends a token in the body of a POST. `ConfirmEmailPage` posts the confirmation token once, on arrival: it keeps
  a ref so that it posts only once, because the link is single-use. The reset token is posted once per submit of the
  new-password form.

## Health feature

The page «Состояние сервиса» at `/health` shows the state of the server and the database. It is in `frontend/src/features/health/`:

| File | What it does |
|---|---|
| `frontend/src/features/health/useHealth.ts` | `useHealth()` runs the query `['health']` against `GET /api/v1/health` and refetches every 10 seconds (`REFRESH_INTERVAL_MS = 10_000`). When the answer has no `data`, the query function throws, so the query is in the error state. |
| `HealthStatus.tsx` | `HealthStatus()` renders the heading and one of the states below. |
| `HealthStatus.module.css` | Styles of the panel, using only tokens. Below 40rem the panel loses its side margins (the literal `40rem`, since a media query cannot read a token). |
| `HealthStatus.test.tsx` | Unit tests of the states; `fetch` is stubbed. |

The texts on the page, exactly as the code has them:

| State | Text |
|---|---|
| Heading, always | `Состояние сервиса` |
| Request pending | `Проверяем…` |
| Request failed, or a non-2xx answer | `Сервер не отвечает` |
| Answer received, server line | `Сервер: работает` |
| Answer received, `database` is `ok` | `База данных: доступна` |
| Answer received, `database` is `unavailable` | `База данных: недоступна` |

The server line shows «работает» once an answer arrives; the answer's `status` is not read. The database line
follows `database` of the answer.

The page refreshes every 10 seconds. The code comment in `useHealth.ts` gives the reason: a database that goes
down shows without a reload. The error state
replaces the list; the last successful answer is not kept on screen.

## Styles and tokens

- `frontend/src/styles/tokens.css` is the one token source, loaded once by `main.tsx`. It holds colors (`--color-background`,
  `--color-surface`, `--color-text`, `--color-text-muted`, `--color-link`, `--color-border`, `--color-ok`, `--color-danger`,
  `--color-focus`, and the `--color-<kind>-text` and `--color-<kind>-bg` pairs described below), spacing (`--space-1` to
  `--space-5`), sizes (`--size-border-width`, `--size-content-width`, `--size-wide-content-width`), the focus ring
  (`--size-focus-width`, `--size-focus-offset`: the visible 2px outline of a focused control), radius (`--radius-md`) and
  fonts (`--font-family-base`, `--font-size-base`, `--font-size-heading`, `--font-size-subheading`).
- **Light and dark.** `:root` holds the light set of colors and sets `color-scheme: light dark`, so the browser draws form
  controls and scrollbars in the theme too. A `@media (prefers-color-scheme: dark)` block holds the dark set: the same
  color tokens under `:root` with dark values. The theme follows the system setting, with no switch in the app; the reasons
  are in [ADR 0084](../adr/0084-approve-change-1-8-visual-system.md).
- **Color values.** Every color token is written as `#rrggbb`: six hex digits, with no `rgb()`, `hsl()` or color names.
- **Contrast pairs.** The text tokens `--color-text`, `--color-text-muted`, `--color-link`, `--color-danger` and `--color-ok`
  sit over `--color-background` and `--color-surface`. Each colored element has a text token over a background token:
  `button-primary`, `button-danger`, `badge-manual`, `badge-rule` and `badge-engine` each have `--color-<kind>-text` over
  `--color-<kind>-bg`. `frontend/src/styles/tokens.test.ts` checks both sets for a contrast of at least 4.5:1 on every such
  pair; it finds the pairs itself, so a new `-text` token with a `-bg` token is checked too.
- **Global rules.** `tokens.css` also sets `a { color: var(--color-link) }` and `overflow-wrap: anywhere` on `body`, so long
  words wrap inside the page.
- **Phone width.** Below `40rem` tables show as cards (each row a block, its cells blocks inside it) and panels lose their
  side margins. A media query cannot read a custom property, so `40rem` is written in each stylesheet that has the rule:
  `frontend/src/components/ui.module.css`, `frontend/src/features/shell/AppShell.module.css` and `frontend/src/features/health/HealthStatus.module.css`.
- Components style themselves with CSS Modules (`*.module.css` next to the component) and use tokens with `var(--…)`.
- **No literals outside tokens.** No color and no `px` size is written outside `tokens.css`, except the literal `40rem` of
  the media queries (see Phone width above). The source guard
  `frontend/src/styles/noLiterals.test.ts` scans every `.css` file except `tokens.css` (CSS comments are skipped) and every
  component `.tsx` file (test files and `frontend/src/test/` excluded) for a hex color, `rgb(`, `hsl(`, a named color or a `px` value;
  it also fails on `style={{` in a `.tsx` file. It checks `px` only, so `rem` and `em` values are not covered by it.
  The generated client in `frontend/src/api/generated/` is not scanned.
- To change a color or a size, change the token, not each component.

## Dev server

- `frontend/vite.config.ts` sets the React plugin, the `/api` proxy and the test settings (`environment`, `setupFiles`,
  `include`, and `TZ`, see [Tests](#tests)).
- The proxy target is `VITE_PROXY_TARGET`, read through `loadEnv`; it defaults to `http://localhost:8000`.
  `docker-compose.yml` sets `http://backend:8000`. The variable is listed in
  [Environment variables](../tech.md#environment-variables).
- `CHOKIDAR_USEPOLLING=true` turns on polling for file changes. The comment in `vite.config.ts` and the compose
  service give the reason: file events do not cross the Windows bind mount.
- In `just dev`, the `frontend` service of `docker-compose.yml` runs the `node:24` image: it enables corepack,
  runs `pnpm install --frozen-lockfile`, then `pnpm exec vite --host 0.0.0.0` on port 5173.

## Tests

- Vitest runs in jsdom (`environment: 'jsdom'`). It picks up `src/**/*.test.{ts,tsx}` and loads
  `frontend/src/test/setup.ts` before each file (`setupFiles`).
- `setup.ts` loads the Jest DOM matchers and, after each test, unmounts the rendered tree and restores the globals
  (`cleanup()`, `vi.unstubAllGlobals()`). Vitest globals are off, so Testing Library does not clean up by itself.
- The page tests render the whole app. They sit in `frontend/src/App.<area>.test.tsx`: `App.guards` (the route guards and «Страница не найдена»), `App.start` (the start page's sign-in and sign-out),
  `App.firstSteps` (the first steps on the start page, FR-50), `App.shell` (the landing page, the header and its sections,
  the menu on a narrow screen, the skip link and the tab titles, FR-48, FR-49 and FR-52), `App.states` (the loading,
  empty and failed pages, FR-51),
  `App.signIn`, `App.registration`, `App.passwordReset`, `App.mailboxes` (the «Почтовые ящики» page), `App.chains` (the header link
  «Переписка», the list and one chain), `App.projects` (the header link «Проекты», the list and the new project),
  `App.projectTree` (the tree of a project), `App.projectFill` (the fill and its rebuild question), `App.chainPlacement` (the «Проект»
  block of a chain page: where the chain is, «Перенести» and «Убрать из проекта»), `App.rules` (the page «Правила» and the header link
  «Правила») `App.ruleExplanations` (the explanation of a rule's placement in the tree and on the chain page) and `App.ruleMoves` (the panel
  «Применить правило сейчас?» after «Создать правило» and «Сохранить»). A scenario test names its FR, for example «FR-17 …»;
  a test of an SPA page without an FR, such as «Вход» or «Страница не найдена», names the page.
- The dates of `format.ts` are in local time. `vite.config.ts` sets `TZ` to `UTC` for the test run (its `test` settings), and
  `App.chains.test.tsx` and `App.mailboxes.test.tsx` set `process.env.TZ = 'UTC'` again at their top, so «14:05» in a test means
  14:05 on any machine. The app itself does not set a zone.
- `App.mailboxes.test.tsx` covers the list and its statuses, «Обновить», the disconnect confirmation (confirm and «Отмена»)
  and the connect form with its refusals. The connect hints have their own files: `App.mailboxConnect.test.tsx` (the service picked
  from the address, FR-53), `App.mailboxConnectErrors.test.tsx` (connecting and the messages, FR-22), `App.mailboxHowTo.test.tsx`
  («Как подключить», FR-54) and `App.mailboxFix.test.tsx` («Как исправить», FR-26). `frontend/src/test/mailboxForm.tsx` holds their
  helpers: the mailbox fixture `mailbox()`, the texts and the `openForm`, `pickService` and `howToBlock` lookups. `App.chains.test.tsx` covers the header link «Переписка», the guard for `/chains`, the
  list with «Показать ещё», the empty list, reading a chain (order, attachments, plain text, line breaks) and the
  «Страница не найдена» answer for another user's chain.
- `frontend/src/test/projectTrees.tsx` is the fixture set of the project tests. It holds the JSON shapes of `ProjectTree` and
  its nodes (`TreeJson`, `CounterpartyJson`, `ThreadJson`, `PlacedChainJson`), the sample tree «Ремонт офиса» (`tree()`, with
  its chains `ESTIMATE`, `ACT` and `FURNITURE`), the fixed ids and texts (`PROJECT_ID`, `FILL`, `EMPTY_PROJECT`, `REBUILD`), and the
  lookups `openProject({ tree }, fill?)`, `chainRow`, `blockOf`, `confirmationWith`, `exactForm` (a count matched whole) and `follows`
  (document order). `openProject` renders the page with a `GET` answer that reads `state.tree`, so a fill answer can replace it.
  Its `placement` is an engine one, a manual one or a rule one (`PlacedChainJson`, with the rule's `RuleRefJson`), so the tests show
  every label.
- `frontend/src/test/chainPlacement.tsx` is the fixture set of the chain page's «Проект» block. It holds the JSON shapes of
  `ChainLocation` and `PlacementMove` (`LocationJson`, `PlacementJson`, `PlacementMoveJson`; `PlacementJson` covers the rule kind too), the projects «Ремонт офиса» (`OFFICE`) and
  «Закупка техники» (`TECH`) with their threads, the placements (`ENGINE_PLACEMENT`, `MANUAL_PLACEMENT`) and the states (`NONE`,
  `EXCLUDED`, `placed(...)`). `openChain(state, options?)` renders the chain page of `CHAIN_ID` with a stateful stub: a `GET` answers
  `state.location`, and a `PUT` or `DELETE` changes it as the server would, unless `options.put` or `options.del` replaces the handler.
  The lookups are `locationAround(projectName)`, `choose(label, option)` for a select of the form, and `rejectedName(message)` for a 422.
- `frontend/src/test/rulesPage.tsx` is the fixture set of the page «Правила». It holds the JSON shapes of `Rule` and `RuleInput`
  (`RuleJson`, `RuleInputJson`), the projects «Ремонт офиса» (`OFFICE`) and «Закупка техники» (`TECH`), three sample rules (`BY_ADDRESS`,
  `BY_DOMAIN`, `BY_SUBJECT`) and the texts of the delete question and of «Такое правило уже есть». `openRules({ rules }, options?)`
  renders `/rules` with a stateful stub: a `POST` appends the rule, a `PUT` replaces it and a `DELETE` removes it, unless `options`
  replaces the handler; `options.extraRoutes` adds routes to the stub, such as the panel's (`moveRoutes`, see `ruleMoves.tsx`).
  The lookups are `ruleRow(value)` (waits for the item of a rule), `listedRules()` (the item texts without the
  buttons), `createForm()`, `editForm()`, `fillCreate(...)`, `chooseIn`, `typeIn`, `pressIn`, `fieldOfIn` and `writesOtherThan`.
- `frontend/src/test/ruleMoves.tsx` is the fixture set of the panel «Применить правило сейчас?». It holds the texts `PANEL_TITLE` and
  `NOTHING`, the chain ids `CHAIN_A` and `CHAIN_B`, the JSON shape of `RuleMove` (`MoveJson`, built by `move(...)`), the sources
  `NOT_PLACED` and `placedIn(project, thread)`, and the answers `movesAnswer` and `appliedAnswer(moved)`. `moveRoutes(ruleId, moves, apply?)`
  gives the `GET` and `POST` routes of one rule, for `extraRoutes`. The lookups are `panel(anchor?)` (the nearest ancestor of the title that
  holds a button, and not the «Создать правило» button), `textOf`, `textShown` and `idsOf` (the sorted `chain_ids` of a request body).
- `frontend/src/App.ruleMoves.test.tsx` covers the panel after «Создать правило» and after «Сохранить»: the listed text for a chain in no
  project, for an engine chain and for a chain in «Неразобранное»; «Применить» with exactly the listed ids and the count the answer gives;
  «Не сейчас» with no request; nothing to move («Подходящих цепочек нет», «Понятно», no «Применить»); and both buttons disabled while
  the request runs.
- `App.rules.test.tsx` covers the header link «Правила», the create form (a rule by address, by domain, by subject words, into
  «Неразобранное», the field messages, no project, a repeated rule, the limit of 200), the list (order, «Правил пока нет», the link
  «Сначала создайте проект», the guard of `/rules`), the edit in place («Изменить», «Сохранить», «Отмена», a repeated edit, a field
  message) and the delete with its confirmation (confirm and «Отмена»). `App.ruleExplanations.test.tsx` covers the explanation of a
  rule placement («Правило · адрес …», «Правило · домен …», «Правило · слова темы «…»») in the tree, in «Неразобранное» and on the chain page.
- `frontend/src/test/appHarness.tsx` provides `renderApp({ path, me?, routes? })`. It moves the browser to `path`,
  stubs `fetch` with `vi.stubGlobal`, and renders `<App queryClient={…} />` with a new `QueryClient` that does not retry.
  `me` is the signed-in user, `{user_id, name, email}`; without it the visitor is signed out.
- The stubbed `fetch` routes each request by `'METHOD /path'`, with the `/api/v1` prefix removed. By default it answers
  `GET /auth/me` (200 with `me`, or 401 `not_signed_in`) and `DELETE /auth/sessions/current` (204). A handler gets the
  request body and the session and returns a `Response`; `signedIn(session, me)` records a sign-in. A request without a
  handler answers 500 with `{"unrouted": …}`, so a missing route shows up in the test.
- `apiError(status, code, fields?)` builds an error body. Its messages come from `MESSAGES` in the harness, a copy of the
  server's Russian messages for the fake API; it has the rule codes `rule_exists` and `too_many_rules` too.
- A handler may answer later: it returns a pending promise, which keeps the request in flight (the fill tests use it to
  check «Заполняется…»). `fieldOf` finds the field of a `<textarea>` too.
- Other helpers in the harness: `heading`, `alertWith`, `rowOf`, `type`, `press`, `fieldOf`, `navigate` (moves the app
  as back and forward do) and `callsTo` (the recorded calls of one route). Each recorded call (`Call`) holds `method`,
  `path` without the `/api/v1` prefix, `query` (the URL's search string, empty without a query) and `body`.
- `START_DATA` is the set of handlers `GET /mailboxes` and `GET /projects`, both answering `[]`. A test that only looks at
  the header passes it as `routes`, so the start page gets its two lists without an unrouted 500.
- `HealthStatus.test.tsx` renders the component with its own `QueryClient` (`retry: false`) and stubs `fetch`
  with `vi.stubGlobal`. The five tests cover the pending state, both database states, a failed request and a
  502 answer.
- `App.visualSystem.test.tsx` covers the visual system of task 1.8 on whole pages. «Отключить» of a mailbox, «Удалить» of a rule
  and «Пересобрать» of a project: the confirming button has the `danger` kind, appears only after the first press, and «Отмена»
  keeps the data. In a project's tree each counterparty and «Неразобранное» is a `<details>` open at first, and its
  `<summary>` folds and unfolds it, each on its own. A chain's placement reason is a badge with its `data-kind`. «Создать проект»
  shows once on the empty «Проекты» and under a listed one. «На главную» is absent from the start page, a project's tree and a
  chain page, and «Страница не найдена» keeps it, leading to `/`.
- `frontend/src/components/Button.test.tsx` covers `Button`: a `<button>` with `type="button"` by default, `secondary` by default, the kinds
  `primary` and `danger` written as `data-kind`, and the native props (`type="submit"`, `disabled`) passed through.
- `frontend/src/features/projects/PlacementBadge.test.tsx` covers the badge's three labels, each with its `data-kind`: «Вручную» (manual),
  «Правило · адрес …» (rule) and «Движок text-1 · сходство 43%» (engine).
- `frontend/src/styles/tokens.test.ts` reads `tokens.css` as text (no browser). It checks that the dark set sits in the
  `prefers-color-scheme: dark` block next to the light one, that `:root` sets `color-scheme: light dark`, that every color token
  is `#rrggbb` and has a value in both sets, and that every text pair described in [Styles and tokens](#styles-and-tokens)
  reaches 4.5:1 in both sets.
- `frontend/src/styles/noLiterals.test.ts` reads the source files as text and fails on a hex color, `rgb(`, `hsl(`, a named color or a `px`
  value outside `tokens.css`, on `style={{` in a `.tsx` file, and on a raw `<button` outside `frontend/src/components/Button.tsx`.
  The rules are in [Styles and tokens](#styles-and-tokens).
- `just test` runs these tests (`frontend-unit` suite). `just check` does not run them; it stays static.

## Build and lint configuration

- `frontend/tsconfig.json` is strict: `strict`, `noUncheckedIndexedAccess`, `noImplicitOverride`,
  `noUnusedLocals`, `noUnusedParameters`, `exactOptionalPropertyTypes`, `verbatimModuleSyntax`. It checks `src` and
  `vite.config.ts`, and emits nothing (`noEmit`). The types are `vite/client` and `@testing-library/jest-dom`.
- `frontend/eslint.config.js` uses typed `strictTypeChecked` and `stylisticTypeChecked` rules, the React and React
  Hooks plugins, `react/no-danger` as an error and `max-lines` 500. `just check` runs ESLint with
  `--max-warnings 0`, so warnings fail it.
- `frontend/.prettierrc.json` sets print width 100, single quotes and trailing commas everywhere.
- `frontend/package.json` scripts: `dev` (Vite), `build` (`tsc --noEmit` then `vite build`), `lint`, `typecheck`,
  `format` and `format:check` (Prettier), `test` (`vitest run`). The recipes that run them are in
  [Dev environment and checks](../tech.md#dev-environment-and-checks).
- Versions of every package are in [Stack](../tech.md#stack).

## How to add a page

1. If the page needs a new route, add it to the backend first, then run `just api-client` and commit the generated
   files with it ([How the client is regenerated](#how-the-client-is-regenerated)). A new behavior needs its approved
   OpenSpec change before the code.
2. Create `frontend/src/features/<area>/<Name>Page.tsx` as a function component with a top comment in English that
   says what the page is and gives its Russian title. Its body is a `Panel` whose `title` is the Russian title.
   Write the texts in Russian in the component; texts shared by several pages go to `frontend/src/messages.ts`.
3. Read server data with a hook in the feature, using `useQuery`, `useInfiniteQuery` or `useMutation`. Call
   `apiClient` and wrap the call in `unwrap` or `unwrapEmpty`. Do not call `fetch`.
4. Add the `<Route>` in `frontend/src/App.tsx` under the guard the page needs: under `RequireGuest` for a page that only a
   signed-out visitor sees; under `RequireUser` for a signed-in page; outside the guards for a page that takes its own
   link token. Under `RequireUser` the page gets `AppLayout` (the header); a page of the guest frame goes under `GuestLayout`
   ([Frames](#frames)). Update the path in
   [Routes and API](../architecture.md#routes-and-api).
5. Read the user only through `useAuth()`.
6. Show the request's error with `ErrorAlert`. For a form, give each `FormField` its message with
   `error={fieldErrors(error).get('<field>')}`, add `noValidate` to the form, and read the values with `formValue`.
7. Put the styles in `<Name>.module.css` next to the component and use the tokens only. Add a token to
   `frontend/src/styles/tokens.css` when a value has none.
8. Add `frontend/src/App.<area>.test.tsx` and render the page with `renderApp` (see [Tests](#tests)). Write one test
   for the main scenario, one for the guard (a signed-out visitor for a page under `RequireUser`) and one
   for each error the page shows. A scenario test names its FR; a test of a page without an FR names the page, as the existing tests do.
9. Update this article: the page's row in [Pages](#pages) and its texts. Then run `just test` and `just check`.
