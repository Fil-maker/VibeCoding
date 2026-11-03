# Frontend

Updated 03.11.2026

**Code:** `frontend/src/`, `frontend/index.html`, `frontend/vite.config.ts`, `frontend/package.json`,
`frontend/tsconfig.json`, `frontend/eslint.config.js`, `frontend/.prettierrc.json`, `frontend/.prettierignore`.
The chain page's «Проект» block is `frontend/src/features/projects/ChainPlacement.tsx`.
The tests are `frontend/src/App.*.test.tsx`, `frontend/src/features/health/HealthStatus.test.tsx` and `frontend/src/test/`.

**Requirements:** the pages and guards carry out [FR-1 … FR-3](../../openspec/specs/organization-registration/spec.md) registration,
[FR-4 … FR-8](../../openspec/specs/sign-in/spec.md) sign-in and password reset,
[FR-17, FR-20 and FR-21](../../openspec/specs/access-boundary/spec.md) the access boundary,
[FR-22, FR-23, FR-24, FR-26 and FR-27](../../openspec/specs/mailboxes/spec.md) the mailbox page,
[FR-30 and FR-31](../../openspec/specs/reply-chains/spec.md) the correspondence pages,
[FR-32 … FR-34](../../openspec/specs/projects/spec.md) the project pages and
[FR-35 … FR-42](../../openspec/specs/chain-placement/spec.md) the fill button of a project and the «Проект» block of a chain,
[FR-43 … FR-45 and FR-47](../../openspec/specs/placement-rules/spec.md) the rules page and the panel after a saved rule, and [FR-37](../../openspec/specs/chain-placement/spec.md)
the rule explanations of a placement. The health page has no requirement:
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
- `App` takes an optional `queryClient` prop. It defaults to the page's query client, which is created once, at
  module load of `App.tsx`, with `createQueryClient()` (see [Query client](#query-client)). Tests pass their own.

## Routing

- The SPA uses react-router 7 in declarative mode: `BrowserRouter`, `Routes`, `Route`, `Navigate` and `Outlet`
  ([ADR 0015](../adr/0015-spa-routing-with-react-router-7.md)).
- The paths and who sees each page are in [Routes and API](../architecture.md#routes-and-api), under «SPA routes».
  This article covers how `App.tsx` nests them:
  - `RequireGuest` wraps the pages for a signed-out visitor: registration, sign-in and the password reset request.
  - `RequireUser` wraps the start page, `/mailboxes`, `/chains`, `/chains/:id`, `/projects`, `/projects/new`, `/projects/:id` and `/rules`.
  - The pages that take their token from the link (email confirmation, new password), the health page
    and the catch-all route stay outside the guards.
- The catch-all route shows `NotFoundPage`. The addresses `/members` and `/invitation` have no route, so they show
  `NotFoundPage` like any unknown path.

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
Every page is a `Panel` whose `title` is its `h1`.

| Page (title) | File | What it does |
|---|---|---|
| «Регистрация» | `frontend/src/features/auth/RegisterPage.tsx` | Fields «Имя», «Email» and «Пароль»; posts name, email and password. Shows the confirmation text with the email, or the mail-failure text when the mail did not go out. The link in the email signs the registrant in. |
| «Подтверждение email» | `frontend/src/features/auth/ConfirmEmailPage.tsx` | Posts the token from the link once, on arrival, then calls `setSession` and goes to `/`. Without a token it shows `Ссылка недействительна или устарела`. |
| «Вход» | `frontend/src/features/auth/SignInPage.tsx` | Posts email and password, then `setSession`; `RequireGuest` takes the user on. Links «Забыли пароль?» and «Регистрация». |
| «Восстановление пароля» | `frontend/src/features/auth/ForgotPasswordPage.tsx` | Posts the email. The answer is the same text for every email. |
| «Новый пароль» | `frontend/src/features/auth/ResetPasswordPage.tsx` | Takes the token from the link, posts it with the new password and shows `Пароль изменён. Теперь можно войти` with a link to «Вход». Without a token it shows the invalid-link text. |
| «VibeCoding» (start page) | `frontend/src/features/home/StartPage.tsx` | Shows the signed-in user's name, the links «Почтовые ящики» (to `/mailboxes`), «Переписка» (to `/chains`), «Проекты» (to `/projects`) and «Правила» (to `/rules`), and the button «Выйти», which ends the session and calls `setSession(null)`. |
| «Почтовые ящики» | `frontend/src/features/mailboxes/MailboxesPage.tsx` | The connected mailboxes, their reading status, «Обновить», «Отключить», and the connect form. See [Mailboxes feature](#mailboxes-feature). |
| «Переписка» | `frontend/src/features/correspondence/ChainsPage.tsx` | The reply chains, the latest first, a page at a time. See [Correspondence feature](#correspondence-feature). |
| The chain's subject (`/chains/:id`) | `frontend/src/features/correspondence/ChainPage.tsx` | One reply chain: the block «Проект» (where the chain is, «Перенести», «Убрать из проекта»), then its emails oldest first, each as plain text. See [Correspondence feature](#correspondence-feature) and [Projects feature](#projects-feature). |
| «Проекты» (`/projects`) | `frontend/src/features/projects/ProjectsPage.tsx` | The user's projects by name, with their chain counts, and the button «Создать проект». See [Projects feature](#projects-feature). |
| «Новый проект» (`/projects/new`) | `frontend/src/features/projects/NewProjectPage.tsx` | Fields «Название» and «Описание»; «Создать» opens the new project. See [Projects feature](#projects-feature). |
| «Правила» (`/rules`) | `frontend/src/features/projects/RulesPage.tsx` | The form of a rule, the user's rules in the order they win, with «Изменить» and «Удалить»; after a rule is saved, the panel «Применить правило сейчас?» (`RuleApplyPanel.tsx`). See [Rules feature](#rules-feature). |
| The project's name (`/projects/:id`) | `frontend/src/features/projects/ProjectPage.tsx` | One project: its description, «Заполнить» with the rebuild question, and the tree of its chains. See [Projects feature](#projects-feature). |
| «Состояние сервиса» | `frontend/src/features/health/HealthStatus.tsx` | The health page; see [Health feature](#health-feature). |
| «Страница не найдена» | `frontend/src/components/NotFoundPage.tsx` | See [Components](#components). |

Forms carry no client-side rules. Each `<form>` has `noValidate`, so the server decides; the per-field messages of
the answer show under their fields (see [Errors and messages](#errors-and-messages)).

## Mailboxes feature

`frontend/src/features/mailboxes/MailboxesPage.tsx` is the whole feature: one file, with `MailboxRow` for a row of the list and
`ConnectForm` for the form. The server side is in [Mail reading](mail-reading.md).

- The page is a `Panel` titled «Почтовые ящики» with a link «На главную» to `/`. It reads `GET /api/v1/mailboxes` under the
  query key `['mailboxes']`. While the query loads it shows `Загрузка…`; with no mailbox it shows `Ящики ещё не подключены`.
- The list is a table with the login, the server, the status and the actions of each mailbox. The page never shows a password.
- **Status text.** The text comes from `statusText` in the page file; the values are exactly:

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
  `Отключить ящик {login}? Прочитанные письма останутся.` and two buttons: «Отключить» (sends `DELETE /api/v1/mailboxes/{mailbox_id}`;
  the button is disabled while the request runs) and «Отмена» (returns the row's buttons, sends nothing). Whatever the answer,
  the confirmation closes. On success the list is invalidated and the mailbox disappears. A failure shows its message in the row.
- **The connect form.** The heading «Подключить ящик» sits above a form with the fields «Сервер IMAP», «Порт» (default `993`,
  set with `defaultValue`), «Логин» and «Пароль приложения» (a password field), and the button «Подключить». It posts
  `POST /api/v1/mailboxes` with `server`, `port` (a number), `login` and `password`. The form has `noValidate`; the server's
  per-field messages show under their fields. When no field has a message, the answer's message shows above the form (for example
  «Этот ящик уже подключён» for `mailbox_exists`). On success the form is cleared and the list is invalidated.

## Correspondence feature

The files are `frontend/src/features/correspondence/`: `ChainsPage.tsx` (the list), `ChainPage.tsx` (one chain),
`ChainPage.module.css` (its styles) and `format.ts` (the date, count and address texts of both pages). The server side is in
[Mail reading](mail-reading.md#reading-a-reply-chain).

- **The list (`/chains`).** The page «Переписка» reads `GET /api/v1/reply-chains` as an infinite query under the key
  `['reply-chains']`. The SPA sends no `limit`, so the server's default page size applies. Each row shows the subject as a link to
  `/chains/{id}`, the participants (`formatAddresses`), the email count (`emailCountLabel`, for example «1 письмо», «2 письма»,
  «5 писем») and the date of the latest email (`formatDate`, date only). With no chain it shows `Писем пока нет: подключите почтовый ящик`.
  The button «Показать ещё» loads the next page with the `cursor` of the last answer. It is disabled while that page loads, and it
  is not shown when the last answer has no `next_cursor`.
- **One chain (`/chains/:id`).** `ChainPage` reads `GET /api/v1/reply-chains/{chain_id}` under the key `['reply-chains', id]`.
  The page title is the chain's subject, and the link «К переписке» goes back to `/chains`. It retries once on an error, except a
  404, which shows `NotFoundPage` (`Страница не найдена`): another user's chain and an unknown id look the same. While loading, and
  on any other error, the page is a «Переписка» panel with `Загрузка…` or the error alert. Under the link «К переписке»
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
`ProjectPage.module.css` (the tree's indents, the description's line breaks and the muted counterparty address), `ChainPlacement.tsx`
  (the «Проект» block of a chain page, see below), `format.ts`, `RulesPage.tsx` and `RuleApplyPanel.tsx` (the page «Правила» and its panel, see [Rules feature](#rules-feature)).
The server side is in [Projects](projects.md). The pages, their routes and their texts are described in
[The SPA](projects.md#the-spa) of that article; this section only says where things live.

- **Texts.** Each page writes its Russian texts in its component. The two texts of the project page's empty tree
  are constants at the top of `ProjectPage.tsx`, next to `REFILL_QUESTION` and `NO_COUNTERPARTY_TITLE`.
- **Formatters (`format.ts`).** `chainCountLabel` and `unassignedCountLabel` pick the Russian plural with `Intl.PluralRules('ru')`,
  as `emailCountLabel` does. `placementLabel(placement)` gives `Вручную` for a placement by hand, `Движок text-1 · сходство 43%`
  for an engine one (the similarity (0–1) is shown in whole percent), and for a rule placement the rule's explanation:
  `Правило · адрес s.petrov@stroymaster.example` (condition `address`), `Правило · домен techsnab.example` (`domain`), and
  `Правило · слова темы «акт работ»` (`subject`; the words go in «»). Each chain row of the tree shows its own placement, and so do
  the chains of «Неразобранное». The same line shows in the «Проект» block of a chain page.
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
  Движок разложит его переписку заново` with the buttons «Пересобрать» and «Отмена»; «Отмена» sends nothing. A project with
  no chain fills at once. While the fill runs the button reads «Заполняется…» and is disabled. On success the page's query data
  is replaced with the answer, and the projects list is invalidated.
- **The start page** links to `/projects` as «Проекты», beside «Почтовые ящики», «Переписка» and «Правила» (`StartPage.tsx`).
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

- **The page.** A `Panel` titled «Правила», wide, with the link «На главную» to `/`. Both queries show `Загрузка…` while they load,
  and a failed query shows its message in an alert.
- **No project.** With no project the page shows the link «Сначала создайте проект» to `/projects/new`, and no form.
- **The form.** Fields «Условие» (a select: «Адрес отправителя», «Домен», «Слова темы»; it starts at «Адрес отправителя»),
  «Значение» (a `FormField`), «Проект» (a select that starts at «Выберите проект», then the user's projects) and «Ветка» (a text
  field with the placeholder «Неразобранное»). The form has `noValidate`. Its button is «Создать правило»; the field messages of
  `condition`, `value`, `project_id` and `thread_name` show under their fields, and any other error shows in an alert above them, only
  when the answer has no field errors (`ErrorAlert error={errors.size > 0 ? null : save.error}`, `RulesPage.tsx`).
  After a created rule the fields are empty again.
- **The list.** Each rule is one item of a list, in the order of the answer (the order the rules win). The item reads the condition's
  title, the value, the project's name and the thread's name, joined as `Адрес отправителя: s.petrov@stroymaster.example → Ремонт офиса → Смета`;
  a rule with no thread name shows `Неразобранное` at the end. The titles are «Адрес отправителя», «Домен» and «Слова темы».
  With no rule the page shows `Правил пока нет`.
- **Edit in place.** «Изменить» replaces the item with the form filled from the rule, with «Сохранить» and «Отмена». «Сохранить»
  sends `PUT /api/v1/rules/{rule_id}`, invalidates the list and returns to the item; a failure shows its messages in that form.
  «Отмена» returns to the item and sends nothing.
- **Delete with a confirmation.** «Удалить» does not send anything at first. It replaces the item's buttons with the question
  `Удалить правило? Цепочки, уже размещённые им, останутся на месте` and two buttons: «Удалить» (sends
  `DELETE /api/v1/rules/{rule_id}`; disabled while it runs) and «Отмена» (returns the buttons, sends nothing). On success the
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
  in `frontend/src/features/health/useHealth.ts`, `Mailbox` and `MailboxConnect` in `MailboxesPage.tsx`, and `EmailView`
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

- `Panel` is the page card: a `<main>` with the title as its only `<h1>`. `wide` widens it to `--size-wide-content-width`.
- `FormField` is a labelled input (`type` `text`, `email` or `password`). It takes an optional `defaultValue`, which the
  input shows at first (the mailbox form uses it for the port `993`). It is uncontrolled: the form reads the values
  from `FormData`. Its label and its message are linked through `useId`.
- `multiline` renders a `<textarea>` with five rows instead of the input (the project description uses it). The `type` prop
  does not apply then. The textarea takes the same `input` look, with `textarea` (vertical resize only).
- `ErrorAlert` is the `role="alert"` paragraph that shows a request's error.
- `NotFoundPage` is a `Panel` titled `Страница не найдена` with the link «На главную» to `/`.
- `formData.ts` exports `formValue(data, name)`, which reads a text field of a submitted form; a missing field counts
  as empty.
- `ui.module.css` holds the shared classes: `panel`, `wide`, `heading`, `subheading`, `form`, `field`, `input`,
  `textarea`, `button`, `links`, `error`, `notice`, `table` and `actions`. They use only tokens.

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
| `HealthStatus.module.css` | Styles of the panel, using only tokens. |
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

- `frontend/src/styles/tokens.css` is the one token source: colors (`--color-background`, `--color-surface`,
  `--color-text`, `--color-text-muted`, `--color-border`, `--color-ok`, `--color-danger`), spacing (`--space-1` to
  `--space-5`), sizes (`--size-border-width`, `--size-content-width`, `--size-wide-content-width`), radius
  (`--radius-md`) and fonts (`--font-family-base`, `--font-size-base`, `--font-size-heading`, `--font-size-subheading`).
  It also sets the `body` font, colors and margin.
- Components style themselves with CSS Modules (`*.module.css` next to the component) and use tokens with
  `var(--…)`. A component does not use raw colors or pixel sizes.
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
- The page tests render the whole app. They sit in `frontend/src/App.<area>.test.tsx`: `App.guards`, `App.start`,
  `App.signIn`, `App.registration`, `App.passwordReset`, `App.mailboxes` (the «Почтовые ящики» page) and `App.chains` (the start
  page links, «Переписка» and one chain), `App.projects` (the list and the new project, with the start page link «Проекты»),
  `App.projectTree` (the tree of a project), `App.projectFill` (the fill and its rebuild question), `App.chainPlacement` (the «Проект»
  block of a chain page: where the chain is, «Перенести» and «Убрать из проекта»), `App.rules` (the page «Правила» and the header link
  «Правила») `App.ruleExplanations` (the explanation of a rule's placement in the tree and on the chain page) and `App.ruleMoves` (the panel
  «Применить правило сейчас?» after «Создать правило» and «Сохранить»). A scenario test names its FR, for example «FR-17 …»;
  a test of an SPA page without an FR, such as «Вход» or «Страница не найдена», names the page.
- The dates of `format.ts` are in local time. `vite.config.ts` sets `TZ` to `UTC` for the test run (its `test` settings), and
  `App.chains.test.tsx` and `App.mailboxes.test.tsx` set `process.env.TZ = 'UTC'` again at their top, so «14:05» in a test means
  14:05 on any machine. The app itself does not set a zone.
- `App.mailboxes.test.tsx` covers the list and its statuses, «Обновить», the disconnect confirmation (confirm and «Отмена»)
  and the connect form with its refusals. `App.chains.test.tsx` covers the start page links, the guard for `/chains`, the
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
  as back and forward do) and `callsTo` (the recorded calls of one route).
- `HealthStatus.test.tsx` renders the component with its own `QueryClient` (`retry: false`) and stubs `fetch`
  with `vi.stubGlobal`. The five tests cover the pending state, both database states, a failed request and a
  502 answer.
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
   link token. Update the path in
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
