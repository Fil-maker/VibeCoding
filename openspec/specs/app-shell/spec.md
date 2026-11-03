# app-shell Specification

## Purpose
The frame of the SPA: what a guest sees first, how a signed-in user moves between the sections, what
a new user is led to do first, and how every page loads, comes up empty and fails.

## Requirements

### Requirement: FR-48 Landing page for guests

A visitor who is not signed in SHALL see at «/» a landing page that says what the app does in three
steps — connect mailboxes read-only, describe a project, get its correspondence as a tree — with
«Зарегистрироваться» and «Войти». The landing page SHALL show no user data. A signed-in user at «/»
SHALL see the start page instead.

#### Scenario: A guest opens the app
- **WHEN** a visitor who is not signed in opens «/»
- **THEN** they see the landing page with «Зарегистрироваться» and «Войти», and «Войти» opens «Вход»

#### Scenario: Registration from the landing page
- **WHEN** a visitor presses «Зарегистрироваться» on the landing page
- **THEN** they see the page «Регистрация»

#### Scenario: A signed-in user opens «/»
- **WHEN** Анна, signed in, opens «/»
- **THEN** she sees the start page and not the landing page

### Requirement: FR-49 Header and sections

Every page of a signed-in user SHALL show a header with «VibeCoding», which opens the start page, the
sections «Проекты», «Переписка», «Почтовые ящики» and «Правила», and the user's name with «Выйти». The
section of the open page SHALL be marked as current, also on a project's or a chain's page. On a narrow
screen the sections, the name and «Выйти» SHALL fold behind «Меню», which opens and closes them.
«Выйти» SHALL end the session and open the landing page.

#### Scenario: Moving between sections
- **WHEN** Анна, signed in, is on «Проекты» and presses «Переписка» in the header
- **THEN** «Переписка» opens and is marked as current, and the header shows «Анна Петрова» and «Выйти»

#### Scenario: A project's page marks «Проекты»
- **WHEN** Анна opens the page of her project «Ремонт офиса»
- **THEN** «Проекты» is marked as current in the header

#### Scenario: Sign-out from the header
- **WHEN** Анна presses «Выйти» in the header on «Правила»
- **THEN** her session ends and she sees the landing page

#### Scenario: The menu on a narrow screen
- **WHEN** Анна opens «Проекты» on a screen 360 px wide and presses «Меню»
- **THEN** the sections, «Анна Петрова» and «Выйти» appear, and after she presses «Переписка» the menu closes and «Переписка» opens

### Requirement: FR-50 First steps on the start page

Until the user has connected a mailbox, created a project and filled a project, the start page SHALL
show «Первые шаги» with the steps «Подключите почтовый ящик», «Создайте проект» and «Заполните проект».
A done step SHALL show «Готово»; a step not done SHALL lead to its page. The steps SHALL count only the
signed-in user's own mailboxes and projects. Once all three are done, the start page SHALL open
«Проекты».

#### Scenario: A new user
- **WHEN** Анна has just registered and opens the start page
- **THEN** she sees «Первые шаги» with no step marked «Готово», and «Подключите почтовый ящик» opens «Почтовые ящики»

#### Scenario: Part of the way
- **WHEN** Анна has connected a mailbox and created the project «Ремонт офиса» that was never filled
- **THEN** the first two steps show «Готово», and «Заполните проект» opens «Ремонт офиса»

#### Scenario: All steps done
- **WHEN** Анна has a mailbox and has filled «Ремонт офиса», and opens the start page
- **THEN** «Проекты» opens and lists «Ремонт офиса»

#### Scenario: Another user's progress does not count
- **WHEN** Вера has a mailbox and a filled project, and Анна, who has neither, opens the start page
- **THEN** Анна sees «Первые шаги» with no step marked «Готово»

### Requirement: FR-51 Loading, empty and failed pages

While a page loads its data it SHALL show «Загрузка…». An empty list SHALL name the next action with a
link to it: «Переписка» — «Писем пока нет: подключите почтовый ящик» with «Подключить ящик»;
«Проекты» — «Проектов пока нет: создайте первый» with «Создать проект»; «Правила» with no project —
«Сначала создайте проект» with «Создать проект». A page whose data failed to load SHALL show the reason
in one alert with «Повторить», which loads it again.

#### Scenario: No correspondence yet
- **WHEN** Анна has no mailbox and opens «Переписка»
- **THEN** she sees «Писем пока нет: подключите почтовый ящик», and «Подключить ящик» opens «Почтовые ящики»

#### Scenario: Rules before any project
- **WHEN** Анна has no project and opens «Правила»
- **THEN** she sees «Сначала создайте проект», and «Создать проект» opens «Новый проект»

#### Scenario: The server does not answer, then answers
- **WHEN** Анна opens «Проекты» while the server does not answer, and presses «Повторить» after it is back
- **THEN** she first sees «Сервер не отвечает» with «Повторить», and then the list of her projects

### Requirement: FR-52 Keyboard and page titles

On every page the first element the keyboard reaches SHALL be «К содержимому», which moves focus to the
page's content; every header item SHALL be reachable by the keyboard, and the focused element SHALL be
visibly marked. The browser tab SHALL be titled «<page title> — VibeCoding», and «VibeCoding» on the
landing page and the start page.

#### Scenario: Skipping the header
- **WHEN** Анна opens «Проекты» and presses Tab and then Enter
- **THEN** «К содержимому» was focused first, and focus moves to the content of «Проекты»

#### Scenario: The tab title
- **WHEN** Анна opens the page of «Ремонт офиса»
- **THEN** the browser tab reads «Ремонт офиса — VibeCoding»

#### Scenario: A page that does not exist
- **WHEN** Анна opens an address that does not exist
- **THEN** she sees «Страница не найдена» in the frame with the header, and the tab reads «Страница не найдена — VibeCoding»
