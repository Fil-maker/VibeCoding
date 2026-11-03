# Tasks

One code cycle (`.claude/skills/feature/code-step.md`) per slice, each with its own sandbox, red check
and `close`: group 1 (frame and routes: FR-48, FR-49, FR-52, FR-6, FR-17), group 2 (start page and page
states: FR-50, FR-51). `test-writer` writes the slice's tests from the brief; `code-writer` writes the
slice's code. Tests sit only at the seam of design «Test seams»: page-level tests through `<App>`.
Implementation docs are updated at `/finish` through `/document`; product docs in group 3.

## 1. Frame and routes (FR-48, FR-49, FR-52, FR-6, FR-17)

- [x] 1.1 `AppLayout`, `GuestLayout`, `AppHeader` with the menu, `HomeRoute`, `LandingPage`, `usePageTitle`; `Panel` renders `<section>`; routes per design «Routes of the SPA»; «Выйти» in the header leads to «/»; the old link list and «Выйти» leave `StartPage`; the narrow breakpoint per design «The header and the menu»; texts per design «Texts» — check - `pnpm --dir frontend lint`, `typecheck` and `build` pass, and the FR-48, FR-49, FR-52 tests pass with the existing suites green
- [x] 1.2 Scenario tests (`test-writer`, sandbox), through `<App>`: FR-48 — a guest at «/» sees the landing page with both links, each opening its page, and no request to the user lists; a signed-in user at «/» does not see it. FR-49 — the four sections, the name and «Выйти» on every user page; `aria-current="page"` on the section and on `/projects/:id` and `/chains/:id`; «Выйти» calls `DELETE /auth/sessions/current` and shows the landing page; «Меню» toggles `aria-expanded`, holds the sections, the name and «Выйти», closes after a section press and on Escape. FR-52 — «К содержимому» is the first focusable element and moves focus to `#content`; the tab title of a section, of a project by its name, of the landing page and of «Страница не найдена» in the frame. FR-6 — after «Выйти» «/» shows the landing page and «Проекты» shows «Вход». FR-17 — a guest at «Проекты» sees «Вход» and lands on «Проекты» after sign-in. Existing suites updated to the new frame without changing what they assert — check - red before the code, green after `tdd_sandbox.py close`

## 2. Start page and page states (FR-50, FR-51)

- [x] 2.1 `StartPage` with «Первые шаги» per design «First steps from the lists the user already has»; `Loading`, `EmptyState`, `LoadError` in `frontend/src/components/`, used by «Проекты», «Переписка», «Почтовые ящики», «Правила», a project's and a chain's page, with the empty texts word for word and the links of design «Texts» — check - `pnpm --dir frontend lint`, `typecheck` and `build` pass, and the FR-50, FR-51 tests pass with the existing suites green
- [x] 2.2 Scenario tests (`test-writer`, sandbox), through `<App>`: FR-50 — no mailbox and no project → three steps, none «Готово», each step's link; a mailbox in error status counts as connected; a mailbox and an unfilled project → two «Готово», «Заполните проект» opens that project; several projects, one filled and one not → still all done; several projects none filled → «Заполните проект» opens the first unfilled one in the list's order; all done → «Проекты» opens; the lists the stub returns for the signed-in user are the only input (no request names a user id). FR-51 — «Загрузка…» before each list answers; the empty «Переписка» with «Подключить ящик», the empty «Проекты» with «Создать проект», «Правила» with no project with «Создать проект»; a failed `GET /projects` shows «Сервер не отвечает» and «Повторить», and after the stub recovers «Повторить» shows the list — check - red before the code, green after `close`

## 3. Product docs

- [x] 3.1 `docs/domain.md`: glossary Landing page and Start page (first steps); requirements map row `app-shell` FR-48…FR-52; «Last FR number: FR-52» at archive; a new edition line — check - `just check` doc facts pass
- [x] 3.2 `docs/ideas.md`: new entry «Search and notifications» (search across the correspondence, notice of new emails, a guided tour) — check - the entry is there with the FRs it would touch

## 4. Verification

- [x] 4.1 `just check` passes with no warnings — check - exit code 0
- [x] 4.2 `/test all` — check - every unit and database suite green, counts reported
- [x] 4.3 Manual flows (`flow-checker`, built-in browser on `just dev`): a guest at «/» → «Зарегистрироваться» → registration; a new user's «Первые шаги» → connect the demo mailbox (`just demo-mail`) → create a project → fill it → «/» opens «Проекты»; at 360 px wide «Меню» opens and closes and the header has no horizontal scroll; Tab from the top reaches «К содержимому», then every header item with a visible focus mark — check - every step PASS

## 5. Done when

- [x] 5.1 A guest who opens «/» sees a landing page that says what the app does in three steps, with «Зарегистрироваться» and «Войти»; any other protected page still sends them to «Вход» and back after sign-in — check - tests of 1.2 and flow 4.3
- [x] 5.2 Every page of a signed-in user has a header with «Проекты», «Переписка», «Почтовые ящики» and «Правила», the current section marked, and the user's name with «Выйти» — check - tests of 1.2
- [x] 5.3 At 360 px wide the sections fold into a menu button — check - flow 4.3
- [x] 5.4 A new user's start page shows three steps (connect a mailbox, create a project, fill it), each marked done or leading to its page; once all three are done, the start page lists the user's projects — check - tests of 2.2 and flow 4.3
- [x] 5.5 Every list page shows one kind of empty state with a link to the next action, one kind of loading state, and errors in one alert — check - tests of 2.2
- [x] 5.6 The keyboard reaches every header item and a «К содержимому» link, focus is visible, and the browser tab title names the page — check - tests of 1.2 and flow 4.3
- [x] 5.7 `just check` and `just test-all` pass — check - 4.1 and 4.2
