# Proposal

## Why

Stage 1 «Project trees» goes to its release (`docs/prd.md` «Stages and scope»), and the SPA still has the look of a
skeleton: one light theme, every button alike, so «Отключить» and «Удалить» look as safe as «Сохранить»;
the placement reason — the core of the invariant «explainable placement» — is plain text lost in the
line; a project tree with many counterparties cannot be folded; tables overflow a phone screen. Task 1.7
added the app frame with a header, which left the old in-page «На главную» links and a second «Создать
проект» on the empty «Проекты» as clutter.

## What Changes

Plan task 1.8 «Visual system»; FR «—». Behavior stays as specified: same pages, texts, actions and
confirmations. Technical change, `skip_specs: true`.

- Light and dark themes: the design tokens get a dark set that follows the system setting
  (`prefers-color-scheme`); body and muted text keep a contrast of at least 4.5:1 in both themes.
- Buttons in three kinds — primary, secondary, danger. Danger marks the confirming buttons of
  «Отключить» (a mailbox), «Удалить» (a rule) and the refill of a project; their confirmation steps stay.
- The placement reason becomes a badge, one look per kind — by hand, by a rule, by the engine — with the
  same text as today («Вручную», «Правило · …», «Движок … · сходство N%»).
- In the project tree each counterparty folds and unfolds; all start unfolded.
- A phone layout: every page reads at 360 px wide without horizontal scrolling; the tables of
  «Проекты», «Переписка» and «Почтовые ящики» become cards there.
- Every color and size lives in `frontend/src/styles/tokens.css`; a test guards it and the contrast.
- The empty «Проекты» shows «Создать проект» once, in its empty state; the button under the list shows
  only when projects are listed.
- The in-page «На главную» links of «Проекты», «Правила», «Почтовые ящики» and «Переписка» go away; the
  header leads home. «Страница не найдена» keeps it, since a guest sees that page without the sections.

Out of scope:

- A manual theme switch in the app — the system setting rules; candidate for `docs/ideas.md`
  «Account settings».
- New texts, pages or actions; remembering which counterparties are folded.
- Confirmation for «Убрать из проекта» — a behavior change, not this task.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None — no requirement changes (`skip_specs: true`). FR-51 already asks for one «Создать проект» in the
empty state of «Проекты».

## Impact

- SPA only: `frontend/src/styles/tokens.css`, `frontend/src/components/` (buttons, badge, tables),
  the CSS modules and the pages of `features/`.
- No API, database or backend change; no new dependency.
- Invariants: none touched. «Explainable placement» keeps every reason text; the badge only shows it
  more clearly.
