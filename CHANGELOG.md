# Changelog

All notable changes for the product's users. The format follows
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/), versions follow
[Semantic Versioning](https://semver.org/). Sections are written by `/release`.

## Unreleased

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
