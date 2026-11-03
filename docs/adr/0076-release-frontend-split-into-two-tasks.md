# Release frontend split into two tasks: first the app shell and user path (new capability, spec deltas), then the visual system (technical, no specs)

Id: 0076 · Date: 03.11.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: 1.7.
- App frame: signed-in pages render inside features/shell/AppLayout (AppHeader with the brand «VibeCoding» linking to «/», the sections «Проекты», «Переписка», «Почтовые ящики», «Правила» with aria-current on the current one, the user's name and «Выйти»; a «Меню» button folds the sections below 40rem); guest pages render in GuestLayout; open pages («/» and the not-found page) use AuthFrame, which picks AppLayout or GuestLayout by the session.
- PageFrame supplies the skip link «К содержимому» and the single <main id="content">; Panel now renders a <section> with the page's only <h1> instead of <main>.
- Panel sets the browser tab title through usePageTitle: «<title> — VibeCoding» by default; its optional prop tabTitle overrides it, and tabTitle={null} gives plain «VibeCoding» (used by the start page and by Waiting).
- Waiting (components/Waiting.tsx) is the page shown while the session loads or the server is unavailable; RequireUser, RequireGuest and AuthFrame use it.
- Shared page states in components/: Loading shows «Загрузка…», EmptyState shows the empty-list text with a link to the next action, LoadError shows the load error in one alert with «Повторить» that refetches. Every list and detail page uses them.
- «/» is HomeRoute: LandingPage for a guest (three steps, «Зарегистрироваться», «Войти», no user data), StartPage for a signed-in user. StartPage reads the user's mailboxes and projects (sharing the cache keys MAILBOXES_KEY and PROJECTS_KEY with their pages), shows «Первые шаги» with three steps marked «Готово» or linked, and redirects to «Проекты» once all three are done.
- BrowserRouter runs with useTransitions={false}; sign-out navigates to «/» inside flushSync before clearing the session, so it lands on the landing page.
- tokens.css gained the focus-ring tokens used for the visible 2px focus outline.

## Decision
Release frontend split into two tasks: first the app shell and user path (new capability, spec deltas), then the visual system (technical, no specs)

## Alternatives
one large change; visual only

## Reason
Две задачи (рекомендую)
