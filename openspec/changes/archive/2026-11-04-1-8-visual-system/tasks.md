# Tasks

Technical change (`skip_specs: true`), so tests come from design «Interface» and the plan row's «Done
when», not from scenarios. One code cycle (`.claude/skills/feature/code-step.md`) for the whole change,
with one sandbox, red check and `close`, covering group 1 (tokens, themes, phone layout) and group 2
(buttons, the badge, the tree, leftover links). `test-writer` writes the tests of both groups from the
brief; `code-writer` writes the code. Existing suites must stay green without changing what they assert.
Implementation docs are updated at `/finish` through `/document`; product docs in group 3.

## 1. Tokens, themes and the phone layout

- [x] 1.1 `tokens.css`: `color-scheme: light dark`, a dark set of every color token under `@media (prefers-color-scheme: dark)`, the tokens the later groups need (button kinds, badge kinds, card spacing); every raw color or size left in the CSS modules moves to a token; tables become cards and panels lose side margins below `40rem`, long words wrap, per design «Tables become cards below `40rem`» — check - `pnpm --dir frontend lint`, `typecheck` and `build` pass and the group's tests pass
- [x] 1.2 Tests (`test-writer`, sandbox) in `frontend/src/styles/`: every color token has a light and a dark value; text, muted text, link, danger and ok text over background and surface, and each button and badge text over its own background, reach 4.5:1 in both sets; no `.css` under `frontend/src` but `tokens.css` and no `.tsx` holds a hex, `rgb(`, `hsl(` or named color or a `px` value, and no `.tsx` uses `style={{` — check - red before the code, green after `tdd_sandbox.py close`

## 2. Buttons, the placement badge, the tree and leftover links

- [x] 2.1 `Button` and `PlacementBadge` per design «Interface»; every `<button>` in `features/` and `components/` uses `Button` with the kind of design «Buttons: a `Button` component with a `kind`»; the tree and the chain's «Проект» block show `PlacementBadge`; counterparties and «Неразобранное» fold with `<details open>`; «Проекты» shows its bottom «Создать проект» only with projects listed; «На главную» leaves «Проекты», «Правила», «Почтовые ящики» and «Переписка» and stays on «Страница не найдена» — check - `pnpm --dir frontend lint`, `typecheck` and `build` pass and the group's tests pass
- [x] 2.2 Tests (`test-writer`, sandbox): `Button` renders a `<button>` with `type="button"` by default and `data-kind` `secondary` by default, `primary` and `danger` when given; `PlacementBadge` shows exactly «Вручную», «Правило · адрес …» and «Движок text-1 · сходство 43%» with `data-kind` `manual`, `rule`, `engine`. Through `<App>`: the confirming «Отключить» of a mailbox, «Удалить» of a rule and the refill confirm are `danger`, appear only after the first press, and «Отмена» leaves everything in place; in a project's tree a counterparty's `<summary>` folds and unfolds its chains, all open at first; the empty «Проекты» has exactly one «Создать проект» and it opens «Новый проект», a listed «Проекты» still has the button; «Проекты», «Правила», «Почтовые ящики», «Переписка» have no «На главную», «Страница не найдена» has it and it leads to «/» — check - red before the code, green after `close`

## 3. Product docs

- [x] 3.1 `docs/ideas.md` «Account settings»: add a manual light/dark switch that overrides the system setting — check - the entry names it, and `just check` doc links pass

## 4. Verification

- [x] 4.1 `just check` passes with no warnings — check - exit code 0
- [x] 4.2 `/test all` — check - every unit and database suite green, counts reported
- [x] 4.3 Manual flows (`flow-checker`, built-in browser on `just dev`, light and dark): at 360 px every page — landing, «Вход», start page, «Проекты», a project's tree, «Переписка», a chain, «Почтовые ящики», «Правила», «Страница не найдена» — has no horizontal scroll and tables read as cards; the theme follows the system setting; the three danger actions still ask before acting; a counterparty folds and unfolds by mouse and by keyboard — check - every step PASS

## 5. Done when

- [x] 5.1 The theme follows the system's light or dark setting, and body text has a contrast of at least 4.5:1 in both themes.
- [x] 5.2 Buttons come in three kinds (primary, secondary, danger); deleting a mailbox or a rule and refilling a project use the danger kind and still ask for confirmation.
- [x] 5.3 The placement reason is a badge: «вручную», «правило» or «движок» with its similarity.
- [x] 5.4 In the project tree each counterparty folds and unfolds.
- [x] 5.5 Every page reads at 360 px without horizontal scrolling; tables become cards there.
- [x] 5.6 No color or pixel size is written outside `tokens.css`.
- [x] 5.7 The empty «Проекты» shows «Создать проект» once, in its empty state; with projects listed, the button «Создать проект» stays under the list.
- [x] 5.8 No page inside the app frame has «На главную»; the page «Страница не найдена» keeps it.
- [x] 5.9 `just check` and `just test-all` pass.
