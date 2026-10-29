# Frontend

Updated 29.10.2026

**Code:** `frontend/src/`, `frontend/index.html`, `frontend/vite.config.ts`, `frontend/package.json`,
`frontend/tsconfig.json`, `frontend/eslint.config.js`, `frontend/.prettierrc.json`, `frontend/.prettierignore`.
The tests are `frontend/src/App.*.test.tsx`, `frontend/src/features/health/HealthStatus.test.tsx` and `frontend/src/test/`.

**Requirements:** the pages and guards carry out [FR-1 … FR-3](../../openspec/specs/organization-registration/spec.md) registration,
[FR-4 … FR-8](../../openspec/specs/sign-in/spec.md) sign-in and password reset, and
[FR-17, FR-20 and FR-21](../../openspec/specs/access-boundary/spec.md) the access boundary. The health page has no requirement:
task 0.1 is a technical change without specs ([ADR 0004](../adr/0004-task-0-1-runs-as-a.md)).

**Design:** [Components and processes](../architecture.md#components-and-processes),
[Repository structure](../architecture.md#repository-structure), [Routes and API](../architecture.md#routes-and-api)
(the SPA route table), [Stack](../tech.md#stack), [Environment variables](../tech.md#environment-variables).

**Related:** [Auth and accounts](auth.md) for the backend side of sign-in, sessions and registration;
[Backend](backend.md).

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
  - `RequireUser` wraps the start page.
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
| «VibeCoding» (start page) | `frontend/src/features/home/StartPage.tsx` | Shows the signed-in user's name and the button «Выйти», which ends the session and calls `setSession(null)`. |
| «Состояние сервиса» | `frontend/src/features/health/HealthStatus.tsx` | The health page; see [Health feature](#health-feature). |
| «Страница не найдена» | `frontend/src/components/NotFoundPage.tsx` | See [Components](#components). |

Forms carry no client-side rules. Each `<form>` has `noValidate`, so the server decides; the per-field messages of
the answer show under their fields (see [Errors and messages](#errors-and-messages)).

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
  in `frontend/src/features/health/useHealth.ts`.

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
- `FormField` is a labelled input (`type` `text`, `email` or `password`). It is uncontrolled: the form reads the values
  from `FormData`. Its label and its message are linked through `useId`.
- `ErrorAlert` is the `role="alert"` paragraph that shows a request's error.
- `NotFoundPage` is a `Panel` titled `Страница не найдена` with the link «На главную» to `/`.
- `formData.ts` exports `formValue(data, name)`, which reads a text field of a submitted form; a missing field counts
  as empty.
- `ui.module.css` holds the shared classes: `panel`, `wide`, `heading`, `subheading`, `form`, `field`, `input`,
  `button`, `links`, `error`, `notice`, `table` and `actions`. They use only tokens.

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

- `frontend/vite.config.ts` sets the React plugin, the `/api` proxy and the test settings.
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
  `App.signIn`, `App.registration` and `App.passwordReset`. A scenario test names its FR, for example «FR-17 …»;
  a test of an SPA page without an FR, such as «Вход» or «Страница не найдена», names the page.
- `frontend/src/test/appHarness.tsx` provides `renderApp({ path, me?, routes? })`. It moves the browser to `path`,
  stubs `fetch` with `vi.stubGlobal`, and renders `<App queryClient={…} />` with a new `QueryClient` that does not retry.
  `me` is the signed-in user, `{user_id, name, email}`; without it the visitor is signed out.
- The stubbed `fetch` routes each request by `'METHOD /path'`, with the `/api/v1` prefix removed. By default it answers
  `GET /auth/me` (200 with `me`, or 401 `not_signed_in`) and `DELETE /auth/sessions/current` (204). A handler gets the
  request body and the session and returns a `Response`; `signedIn(session, me)` records a sign-in. A request without a
  handler answers 500 with `{"unrouted": …}`, so a missing route shows up in the test.
- `apiError(status, code, fields?)` builds an error body. Its messages come from `MESSAGES` in the harness, a copy of the
  server's Russian messages for the fake API.
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
