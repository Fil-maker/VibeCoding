# Visual system

Date: 04.11.2026 · Task: 1.8 · Change: 1-8-visual-system

## Goal

Before the release of stage 1 the SPA should stop looking like a draft. The change is technical
(`skip_specs`): no requirement changes, because FR-51 already asks for one «Создать проект» in the empty
state. No product invariant is touched; the placement reason text stays as it is. Two small clean-ups from
the user's input were folded into the same task: remove the second «Создать проект» on the empty
«Проекты» and remove the old «На главную» links.

Out of scope: a manual theme switch (moved to `docs/ideas.md`, «Account settings»), remembering folded
nodes, a confirmation for «Убрать из проекта».

## What was done

- **Themes.** `frontend/src/styles/tokens.css` got a second set of colour tokens under
  `prefers-color-scheme: dark`; text contrast is at least 4.5:1 in both themes, checked by a Vitest test.
- **Button.** `frontend/src/components/Button.tsx` with `kind` primary / secondary / danger; all buttons go
  through it. Danger is used by the confirming «Отключить» (mailbox), «Удалить» (rule) and the project
  refill «Пересобрать». The header buttons «Меню» and «Выйти» also moved to `Button` (beyond the brief,
  accepted).
- **PlacementBadge.** The placement reason is shown as a badge with a `data-kind` (manual / rule /
  engine); the text is the same as before.
- **Project tree.** Counterparties and «Неразобранное» fold with `<details open>`; folding works by mouse
  and by Enter and Space.
- **Phone.** Below `40rem` tables display as cards, long addresses wrap.
- **Leftover links.** The bottom «Создать проект» shows only when the list of projects is not empty;
  «На главную» left «Проекты», «Правила», «Почтовые ящики» and «Переписка» and stays on
  «Страница не найдена».
- **Tests.** Five test files, including two guards: no colour or pixel literals outside `tokens.css`, and
  no raw `<button` in the sources. One `test-auditor` pass found 10 weak spots; the test writer fixed all.
- **Docs.** `docs/ideas.md` got the theme-switch idea; `docs/plan.md` row 1.8 got both removals (edition
  0.19); the frontend guide and architecture were updated; ADRs 0081–0084 were written.
- **Checks at finish.** `just check` all 17 passed; tests: backend-unit 109, frontend-unit 304, db 311,
  all green. Manual check on `just dev` at 360 px in light and dark: 11 pages, no horizontal scroll; the
  three danger actions ask first and «Отмена» changes nothing. `invariant-reviewer`: no BLOCKER or
  IMPORTANT; two MINOR dropped (the opacity literal is neither a colour nor a pixel size and was an
  accepted deviation; the `Button` import order is covered by no rule). Doc-checkers found four
  overstatements in the new docs (primary «always submit», Button props, the `<button` guard scope,
  noLiterals «sizes»), all fixed.

## Key questions to the AI

- How to carry the user's two bullets («убрать вторую «Создать проект» на пустой странице «Проекты»;
  убрать старые ссылки «На главную»»)? The user chose «Добавить в задачу 1.8» rather than a separate change.
- Keep «На главную» on «Страница не найдена»? The user chose «Оставить (рекомендую)».
- Write this into the row of 1.8? Answer: «Да (рекомендую)».
- Approve change 1-8-visual-system? Answer: «Да (рекомендую)».
- The worktree had no `.env`, which the database tests and the 360 px check need. The user chose
  «Скопировать .env.example (рекомендую)».
- At the documentation step: confirm decisions 1–4 for ADRs and drop the local `.env` one? Answer:
  «Да, 1–4, снять 5 (Recommended)».

## Decisions

| Decision | Alternatives | Reason | Who |
| --- | --- | --- | --- |
| Fold the removal of the duplicate «Создать проект» on the empty «Проекты» and of the old «На главную» links into task 1.8 «Visual system» | A separate minor change | Пользователь выбрал «Добавить в задачу 1.8» | [human] |
| Keep «На главную» on the page «Страница не найдена» | Remove it everywhere | Пользователь выбрал «Оставить»: гость видит 404 без шапки с разделами, ссылка — его путь назад | [human] |
| Plan row 1.8 gets the two removals in its task text and «Done when»; plan edition 0.19 | - | Пользователь одобрил черновик строки: «Да» | [human] |
| Approve change 1-8-visual-system (skip_specs): dark tokens under prefers-color-scheme, Button with kind, PlacementBadge keeping today's texts, <details> folding, tables as cards below 40rem, the leftover links removed | data-theme switch; stylelint; CSS-only button classes; short lowercase badges with a tooltip | Пользователь одобрил: «Да» | [human] |

## Mistakes and lessons

- **The plan row did not match the app.** «Done when» said «удаление ящика», but the app button is
  «Отключить», and the badges were written in lowercase («вручную») while the scenarios keep the texts
  «Вручную», «Правило · …», «Движок … · сходство N%». The design resolved both as a clarification, not a
  change of the row. A check of the row's wording against the UI texts before writing it would have caught
  it.
- **No auditor briefs for a technical change.** With `skip_specs` the sandbox `red` step wrote no briefs
  (no scenarios), so one `test-auditor` was run by hand over all five test files. It found 10 weak spots
  (for example a missing empty-state check for «Создать проект», no check of «На главную» on every
  in-frame page, no guard against raw `<button`). Running the auditor by default for `skip_specs` changes
  would have caught them in the first pass.
- **Overstated docs.** Doc-checkers found four overstatements in the new docs (primary «always submit»,
  Button props, the `<button` guard scope, noLiterals «sizes»); comparing each claim with the code caught
  them.
- **Missing `.env`.** The worktree had none; a local one was made from `.env.example` with a generated
  `MAILBOX_ENCRYPTION_KEY`. The shared dev database holds older mailboxes that do not decrypt with this
  key (`SecretBoxError` in the backend log) — pre-existing data, not this change.
- **Code writer went beyond the brief** (header buttons, a focus ring on `.button`, a global link colour
  and `overflow-wrap: anywhere` in `tokens.css`, `opacity` for a disabled button); all accepted after
  review.

## What remains

- The start page was not opened by hand as a separate view: the test account had a mailbox, so `/` showed
  «Проекты». Unit tests cover that it has no «На главную».
- The manual theme switch lives in `docs/ideas.md` («Account settings»).
- Folded nodes are not remembered, and «Убрать из проекта» has no confirmation (both out of scope).
