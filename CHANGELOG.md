# Changelog

All notable changes for the product's users. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow
[Semantic Versioning](https://semver.org/). Sections are written by `/release`.

## Unreleased

## [0.7.0] - 2026-11-05

### Added

- Editing a project: «Изменить» on its page changes the name and the description without moving
  any chain; after a new description a filled project shows a hint to fill it again.
- Deleting a project after a confirmation that names how many chains leave it and how many rules
  are deleted; its chains stay in «Переписка» as taken out by hand with all their emails, and the
  rules leading into it are deleted.

## [0.6.0] - 2026-11-04

### Added

- Connecting a mailbox starts with its address: for Яндекс Почта, Mail.ru, Gmail and iCloud the app
  fills the server and the port and shows «Как подключить» with the steps and a link to the
  service's official help; any other address gets «Другой» with a hint where to find the server.
- «Почтовые ящики» explains that the app only reads the mailbox and why an app password is needed.
- A mailbox that cannot sign in shows «Как исправить» with the steps of its service.

## [0.5.0] - 2026-11-04

### Added

- Applying a saved rule at once: after a rule is created or edited, «Правила» lists the chains it
  would move and moves them on «Применить»; chains placed by hand or taken out stay.
- One header on every signed-in page, folding into «Меню» on a narrow screen.
- A landing page for guests and «Первые шаги» until a mailbox is connected and a project is filled.
- A dark theme that follows the system setting.

### Changed

- Loading, empty and failed pages share one look; every browser tab is titled «<page> — VibeCoding».
- Buttons and placement badges look the same everywhere; counterparties and «Неразобранное» fold;
  tables become cards on a narrow screen.

### Fixed

- Signing out lands on the landing page.
- The empty «Проекты» shows «Создать проект» only once.

## [0.4.0] - 2026-11-03

### Added

- The page «Правила»: rules by sender address, domain or subject words, each with a target project
  and a thread name; rules can be edited and deleted, up to 200 per user.
- A new chain that matches a rule goes into the rule's project and thread before the engine compares
  it, also into a project not filled yet; a missing thread is created.
- «Заполнить» places the chains matching the project's rules by those rules first and gives the rest
  to the engine.
- A chain placed by a rule shows «Правило» and the rule as it was when it placed the chain.

### Changed

- When several rules match a chain, an address wins over a domain, a domain over subject words, then
  the earlier rule.
- Rules never move a chain placed by hand or taken out of projects, and a new rule moves no chain
  already placed.

## [0.3.0] - 2026-11-02

### Added

- Moving a chain by hand on its page into a thread of any project, into «Неразобранное» or into a new
  thread; the chain then shows «Вручную».
- Chains placed by hand never move: not with new emails, a mailbox reading or «Заполнить».
- «Убрать из проекта» takes a chain out of its project for good; the app never places it again by itself.

### Changed

- «Заполнить» on a filled project keeps the chains placed by hand and their threads and lays out only
  the rest again.
- Every chain in a project tree shows whether it was placed by hand or by the engine.

## [0.2.0] - 2026-11-02

### Added

- Connecting several mailboxes over IMAP, read-only: the app never sends, deletes or marks emails;
  the app password is stored encrypted and deleted when the mailbox is disconnected.
- Reading Inbox and Sent of the last 12 months in the background every 5 minutes and on «Обновить».
- Reply chains: the emails of all mailboxes are joined into whole exchanges, each email shown once.
- Projects with a name and a description, and the list «Проекты».
- «Заполнить» lays out a project's correspondence as a tree of counterparties and threads; chains the
  app is not sure of go to «Неразобранное».
- Every placed chain shows why it is there: «Движок text-1 · сходство N%».
- New emails take their place in the tree after each reading without moving chains already placed.
- Filling a project again asks first and gives the same tree from the same emails.

## [0.1.0] - 2026-10-29

### Added

- Registration with a name, an email and a password, confirmed by an emailed link.
- Sign-in with email and password, a 15-minute lock after 5 wrong passwords, 14-day sessions and
  sign-out on one device.
- Password reset by an emailed link valid for 1 hour; the new password ends every session.
- Every user sees only their own data; requests from other sites are refused.
- A service page that shows whether the server and the database answer.
