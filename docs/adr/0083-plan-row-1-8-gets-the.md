# Plan row 1.8 gets the two removals in its task text and «Done when»; plan edition 0.19

Id: 0083 · Date: 04.11.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: 1.8.
- Button (frontend/src/components/Button.tsx) is the one button of the SPA: native <button> props plus kind 'primary' | 'secondary' | 'danger' (default secondary); type defaults to "button"; the kind is exposed as data-kind; classes .button, .primary, .dangerButton live in components/ui.module.css. A source test (styles/noLiterals.test.ts) fails on a raw <button outside components/Button.tsx.
- Danger kind: the confirming buttons of «Отключить» of a mailbox, «Удалить» of a rule and «Пересобрать» of a project refill; they still appear only after the first press, and «Отмена» keeps everything. The header's «Меню» and «Выйти» are secondary Buttons.
- A disabled Button dims with opacity; .button has a focus ring.
- PlacementBadge (frontend/src/features/projects/PlacementBadge.tsx, PlacementBadge.module.css) shows the exact text of placementLabel(placement) («Вручную», «Правило · адрес …», «Движок text-1 · сходство 43%») with data-kind manual, rule or engine; the color only repeats the text. It is used in the project tree and the chain's «Проект» block.
- In a project's tree each counterparty and «Неразобранное» are <details open> with a <summary>: open at first, they fold and unfold by mouse and keyboard.
- tokens.css sets color-scheme: light dark on :root and holds a dark set of every color token in @media (prefers-color-scheme: dark) { :root { … } }; every --color-* token is #rrggbb. Text tokens --color-text, --color-text-muted, --color-link, --color-danger, --color-ok sit over --color-background and --color-surface; button-primary, button-danger, badge-manual, badge-rule, badge-engine each have --color-<kind>-text over --color-<kind>-bg. tokens.test.ts checks both sets and a contrast of at least 4.5:1 for every -text/-bg pair and the text tokens over background and surface.
- tokens.css also holds a global a { color: var(--color-link) } and overflow-wrap: anywhere on body. Below 40rem (media queries use the literal 40rem since a media query cannot read a custom property) tables display as blocks (cards) and panels lose side margins.
- No color or pixel size is written outside tokens.css: noLiterals.test.ts scans every .css under frontend/src but tokens.css and every .tsx for hex, rgb(, hsl(, named colors and px values, and fails on style={{ in a .tsx.
- The empty «Проекты» shows «Создать проект» once, in its empty state; with projects listed the button stays under the list. «На главную» left «Проекты», «Правила», «Почтовые ящики» and «Переписка»; only «Страница не найдена» keeps it, leading to /.

## Decision
Plan row 1.8 gets the two removals in its task text and «Done when»; plan edition 0.19

## Alternatives
none recorded

## Reason
Пользователь одобрил черновик строки: «Да»
