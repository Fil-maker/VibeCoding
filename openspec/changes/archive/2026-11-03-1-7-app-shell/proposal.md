# Proposal

## Why

The app is about to be shown to its first users (`docs/prd.md` «Users»: anyone who registers on their
own), but the SPA still looks like a skeleton. A visitor lands on a bare sign-in form that does not
say what the app does. A signed-in user reaches the sections only from the start page, which shows a
name and four links and no hint of what to do first. Every page is a separate card with no way back,
and sign-out is only on the start page. The value the product promises — describe a project, get its
correspondence as a tree — needs three steps (connect a mailbox, create a project, fill it), and
nothing leads a new user through them. This is task 1.7 «App shell and user path» of `docs/plan.md`.
The visual system (themes, button kinds, badges, phone layout of every page) is task 1.8.

## What Changes

- A guest who opens «/» sees a landing page: what the app does, three steps, and «Зарегистрироваться»
  and «Войти». Every other protected page still sends the guest to «Вход» and back after sign-in.
  Sign-out leads to the landing page.
- Every page of a signed-in user sits in one frame: a header with «VibeCoding» (to the start page), the
  sections «Проекты», «Переписка», «Почтовые ящики» and «Правила» with the current one marked, and the
  user's name with «Выйти». On a narrow screen the sections and the user's menu fold behind «Меню».
- The start page of a user who has not finished the three steps shows «Первые шаги»: connect a mailbox,
  create a project, fill it, each marked «Готово» or leading to its page. Once all three are done, the
  start page opens «Проекты».
- Pages load, come up empty and fail the same way: «Загрузка…» while loading; an empty list names the
  next action with a link to it; a failed load shows its reason with «Повторить».
- The keyboard reaches a «К содержимому» link first and every header item; focus is visible; the browser
  tab is titled «<page title> — VibeCoding».

Out of scope:
- Themes, button kinds, placement badges, a folding project tree, phone layout of the pages' content —
  task 1.8 «Visual system».
- Account settings (name, password, email) from the user's menu — already in `docs/ideas.md` «Account
  settings».
- Search across the correspondence, notifications of new emails, a guided tour with overlays — a new entry
  «Search and notifications», added to the ideas by task 3.2.

## Capabilities

### New Capabilities

- `app-shell`: the frame of the SPA — the landing page for guests, the header and sections, the first
  steps on the start page, the common page states and the page titles. FR-48…FR-52.

### Modified Capabilities

- `access-boundary`: FR-17 «Protected pages and actions need a signed-in user» — the landing page is
  open to guests; the scenario opens «Проекты» instead of the start page.
- `sign-in`: FR-6 «Session lifetime and sign-out» — after «Выйти» and on an expired session the start
  address shows the landing page; a protected page still shows «Вход».

## Impact

- Product invariants: **Access boundary** — touched: the landing page is the one new page open to
  guests and shows no user data; the first steps count only the signed-in user's own mailboxes and
  projects, from the lists the API already returns for that user. The others: none.
- SPA only: a layout route with the header, the landing page, the start page with the first steps,
  shared components for loading, empty and failed states, a page-title hook; `Panel` no longer renders
  `<main>`. No API change, no new dependency, no migration.
- Docs: `docs/domain.md` (glossary: Landing page, Start page; requirements map: `app-shell`;
  «Last FR number»), `docs/ideas.md` («Search and notifications»), `docs/architecture.md` and the SPA
  guide through `/document`.
