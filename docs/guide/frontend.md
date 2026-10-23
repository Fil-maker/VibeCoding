# Frontend

Updated 23.10.2026

**Code:** `frontend/src/`, `frontend/index.html`, `frontend/vite.config.ts`, `frontend/package.json`,
`frontend/tsconfig.json`, `frontend/eslint.config.js`, `frontend/.prettierrc.json`, `frontend/.prettierignore`.

**Requirements:** none. Task 0.1 is a technical change without specs ([ADR 0004](../adr/0004-task-0-1-runs-as-a.md)).

**Design:** [Components and processes](../architecture.md#components-and-processes),
[Repository structure](../architecture.md#repository-structure), [Routes and API](../architecture.md#routes-and-api),
[Stack](../tech.md#stack), [Environment variables](../tech.md#environment-variables).

**Related:** [Backend](backend.md).

## Entry and providers

- `frontend/index.html` is the page shell: `lang="ru"`, title `VibeCoding`, an empty `<div id="root">`, and
  the module script `/src/main.tsx`.
- `frontend/src/main.tsx` finds `#root`, throws when it is missing, and renders `<App />` inside `StrictMode`.
  It imports the design tokens (`frontend/src/styles/tokens.css`) once, so every component gets them.
- `frontend/src/App.tsx` is the root component. Its only provider is `QueryClientProvider`; it renders the
  health page `HealthStatus`. There is no router and no other provider yet.
- The query client is created once, at module load of `App.tsx`, with `createQueryClient()`, and lives for the
  whole page.

## API client

Server data reaches the SPA only through the generated client; components never call `fetch` directly.

- `frontend/src/api/client.ts` exports `apiClient`, an `openapi-fetch` client typed by `paths` from
  `frontend/src/api/generated/schema.ts`. Its `baseUrl` is `window.location.origin`, so requests go to the page's
  own origin; in development the Vite dev server forwards `/api` (see [Dev server](#dev-server)).
- The `fetch` option calls `globalThis.fetch` on each call. The code comment in `client.ts` gives the reason:
  tests can replace the global `fetch`.
- A call looks like `apiClient.GET('/api/v1/health')`. It returns `{ data, error }`; `data` is undefined on a
  non-2xx answer. A network failure throws from `fetch`. Both end in the query's error state, which the page
  shows as «Сервер не отвечает».
- Schema types come from `components['schemas'][...]`, for example `HealthStatus` in `frontend/src/features/health/useHealth.ts`.

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

## Query client

- `frontend/src/api/queryClient.ts` exports `createQueryClient()`, which returns a TanStack Query `QueryClient`
  with one retry for queries (`QUERY_RETRIES = 1`). The code comment in `queryClient.ts` gives the reason: a missing
  backend is reported within seconds instead of after the library's default backoff.
- Queries are wrapped in one hook per feature, for example `useHealth()`. Components use the hook, not the client.

## Health feature

The page «Состояние сервиса» is the only feature. It is in `frontend/src/features/health/`:

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

- `frontend/src/styles/tokens.css` is the one token source: colors (`--color-*`), spacing (`--space-1` to
  `--space-5`), sizes (`--size-border-width`, `--size-content-width`), radius (`--radius-md`) and fonts
  (`--font-family-base`, `--font-size-base`, `--font-size-heading`). It also sets the `body` font, colors and margin.
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
- Known issue: the frontend container downloads pnpm through corepack on every start. On this machine Docker's
  embedded DNS intermittently fails (`EAI_AGAIN` for registry.npmjs.org), so the first `just dev` may need a retry.

## Tests

- Vitest runs in jsdom (`environment: 'jsdom'`). It picks up `src/**/*.test.{ts,tsx}` and loads
  `frontend/src/test/setup.ts` before each file (`setupFiles`).
- `setup.ts` loads the Jest DOM matchers and, after each test, unmounts the rendered tree and restores the globals
  (`cleanup()`, `vi.unstubAllGlobals()`). Vitest globals are off, so Testing Library does not clean up by itself.
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
