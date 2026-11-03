# Design

## Context

The SPA (`frontend/src`) has one route tree in `App.tsx`: guest pages under `RequireGuest`, user pages
under `RequireUser`, and `NotFoundPage` for the rest. Every page renders `Panel`, a centered card that
is the page's `<main>` and its only `<h1>`. There is no shared frame: the start page (`StartPage`) holds
the only links to the sections and the only «Выйти». Loading shows `LOADING_MESSAGE`, errors go through
`ErrorAlert`, and empty lists are plain paragraphs, each page in its own way. The API already returns
everything the new frame needs for the signed-in user: `GET /auth/me` (name), `GET /mailboxes`,
`GET /projects` (`ProjectSummary.filled`). Styling uses CSS modules over `styles/tokens.css`
(`.claude/rules/frontend.md`); session decision 4 keeps it that way, with no UI library.

## Goals / Non-Goals

**Goals:**
- One layout route for the pages of a signed-in user, with the header of FR-49 and the skip link of
  FR-52.
- «/» chosen by the auth state: the landing page (FR-48) or the start page (FR-50).
- Shared components for the loading, empty and failed states of FR-51, used by every list page.
- A page title set in one place, from the page's heading.

**Non-Goals:**
- Themes, button kinds, badges, a folding tree, phone layout of the pages' content — task 1.8.
- Any API, backend or database change; any new dependency.

## Decisions

### A layout route under `RequireUser`

`RequireUser` keeps the guard; its children move under a new `AppLayout` route element that renders the
skip link, the header and `<main id="content" tabIndex={-1}>` around an `<Outlet />`. `Panel` stops
rendering `<main>` and renders a `<section>` with the `<h1>`. `NotFoundPage` sits under `AppLayout` when
the user is signed in and under a guest frame otherwise. Guest pages (`/sign-in`, `/register`,
`/forgot-password`, `/confirm-email`, `/reset-password`) get a `GuestLayout` with the skip link, a header
with «VibeCoding» (to «/») and the same `<main>`.
Alternatives: the header inside `Panel` — rejected: every page would render and re-fetch the frame,
and a page without `Panel` would lose it; a header outside the router — rejected: it needs the router
for the current section and sign-out navigation.

### «/» chosen by the auth state

A `HomeRoute` element at «/» outside both guards: while the auth state loads it shows the guards'
waiting panel; signed out → `LandingPage` in `GuestLayout`; signed in → `StartPage` in `AppLayout`.
Alternatives: the landing page at `/welcome` with «/» protected — rejected by session decision 2
(the landing page is what a guest sees at «/») and because a shared link to the app should not open a
bare sign-in form.

### First steps from the lists the user already has

`StartPage` reads `GET /mailboxes` and `GET /projects` through the query keys the sections already use,
so the data is shared with «Почтовые ящики» and «Проекты». Step 1 is done with at least one mailbox in
any status; step 2 with at least one project; step 3 with at least one project whose `filled` is true.
«Заполните проект» opens the first project not filled (in the list's order), or «Проекты» when there is
none. All three done → `<Navigate to="/projects" replace />`.
Alternatives: a new `GET /me/progress` — rejected: no new API for data the lists already carry, and a
second source could disagree with the lists; keeping the old link list on the start page for a returning
user — rejected: it duplicates the header.

### The header and the menu

`AppHeader` renders a `<nav aria-label="Разделы">` with `NavLink`s; a section is current when the path
is the section or starts with it plus «/» (`/projects/...`, `/chains/...`), marked with
`aria-current="page"`. The name and «Выйти» follow. A `<button aria-expanded aria-controls>` «Меню» is
always in the DOM; CSS shows it and hides the folded list below the narrow breakpoint (`40rem`; a media
query cannot read a custom property, so the breakpoint is the one length written outside `tokens.css`,
with a comment). The menu closes on a section press, on a route change and on Escape. «Выйти» runs the
existing `DELETE /auth/sessions/current`, clears the session and navigates to «/».
Alternatives: a dropdown library — rejected by session decision 4; a side bar — rejected: four sections
fit one line, and a side bar takes width the project tree needs.

### Shared page states

Three components in `frontend/src/components/`: `Loading` («Загрузка…», `role="status"`), `EmptyState`
(the message and an optional link with its label), `LoadError` (the reason from the existing
`ErrorAlert` mapping in `role="alert"`, plus «Повторить», which calls the query's `refetch`). Every list
page («Проекты», «Переписка», «Почтовые ящики», «Правила», a project's and a chain's page) uses them;
the existing empty texts stay word for word.

### Page title in `Panel`

`Panel` sets `document.title` to «<title> — VibeCoding» through a `usePageTitle` hook; the landing page
and the start page use «VibeCoding». One place, because every page already passes its heading to
`Panel`.

### Who may do what

No new action and no new API. The landing page reads no user data. The header and the start page read
only `GET /auth/me`, `GET /mailboxes` and `GET /projects`, which return the signed-in user's data only
(FR-21); no request carries a user identifier.

## Interface

### Routes of the SPA

| Path | Guest | Signed-in user |
|---|---|---|
| `/` | `LandingPage` | `StartPage`, or redirect to `/projects` when the first steps are done |
| `/sign-in`, `/register`, `/forgot-password` | the page in `GuestLayout` | redirect to `next` or `/` (unchanged) |
| `/confirm-email`, `/reset-password` | the page in `GuestLayout` | the page in `GuestLayout` |
| `/projects`, `/projects/new`, `/projects/:id`, `/chains`, `/chains/:id`, `/mailboxes`, `/rules` | redirect to `/sign-in?next=…` (unchanged) | the page in `AppLayout` |
| any other | `NotFoundPage` in `GuestLayout` | `NotFoundPage` in `AppLayout` |

### Texts

- Landing: `<h1>` «Переписка по проектам — в одном дереве»; lead «VibeCoding собирает письма из всех
  ваших ящиков и раскладывает их по проектам: проект → контрагент → ветка.»; an ordered list
  «Подключите почтовые ящики — только для чтения», «Опишите проект в нескольких предложениях»,
  «Получите дерево переписки — и объяснение, почему каждая цепочка на своём месте»; links
  «Зарегистрироваться» (`/register`) and «Войти» (`/sign-in`).
- Header: «VibeCoding», «Проекты», «Переписка», «Почтовые ящики», «Правила», the user's name, «Выйти»,
  «Меню»; skip link «К содержимому».
- Start page: `<h1>` «Первые шаги»; steps «Подключите почтовый ящик» (`/mailboxes`), «Создайте проект»
  (`/projects/new`), «Заполните проект»; a done step shows «Готово» and no link.
- Empty and failed states: «Подключить ящик» (`/mailboxes`) on «Переписка»; «Создать проект»
  (`/projects/new`) on «Проекты» and on «Правила» with no project; «Повторить».

### Components

- `AppLayout`, `GuestLayout` — route elements with `<Outlet />`.
- `Loading()`, `EmptyState({message, action?: {to, label}})`, `LoadError({error, onRetry})`.
- `usePageTitle(title: string | null)` — null gives «VibeCoding».
- `Panel({title, wide?, children})` — unchanged props; renders `<section>` instead of `<main>`.

### Test seams

Page-level tests through `<App>` with the stubbed fetch of `frontend/src/test/appHarness.tsx`; no new
seam. jsdom applies no media queries, so the tests press «Меню» and check `aria-expanded` and what the
menu holds; the narrow layout itself is checked in the browser (tasks «Verification»).

## Risks / Trade-offs

- Existing page tests find «Выйти» and the section links on the start page and `<main>` per page →
  they are updated in the sandbox with the new frame; a scenario that changes meaning is only FR-6 and
  FR-17, rewritten in this change.
- The start page fetches two lists on every visit → the queries are cached and shared with the
  sections; both lists are small (one user's mailboxes and projects).
- The redirect from «/» to «Проекты» hides the first steps once done → by design (FR-50); nothing is
  lost, since the steps only point to the sections.

## Migration Plan

No data and no API change. Rollback is reverting the SPA commit.
