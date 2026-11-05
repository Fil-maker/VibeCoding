# Tasks

## 1. Scenario tests (test-writer, TDD sandbox)

- [x] 1.1 Backend unit tests of the parsing and the fake mail reader: an attachment list with names and decoded sizes in `walk()` order, two files with one name, a part without a name skipped; `fetch_message` sends only read-only commands, compares UIDVALIDITY and answers «gone» for a changed one or an empty answer — check — red against the current code.
- [x] 1.2 Backend integration tests for FR-57, FR-58 and FR-25 (`test_attachment_download.py`) on the fake reader: the bytes and headers of a download, the second of two same-named files, a copy in a disconnected and a connected mailbox, two downloads the same with nothing stored, an HTML attachment answered as `application/octet-stream` with `nosniff`, another user's email and an out-of-range index answering 404 with no connection made, disconnected → 409, gone → 410, sign-in refused → 502 and unreachable → 504 with the mailbox status unchanged, the email staying unseen — check — red against the current code.
- [x] 1.3 Backend integration tests for FR-31: `attachments` with index, name and size on a newly read email; an email migrated from `attachment_names` with null sizes — check — red against the current code.
- [x] 1.4 Test factories: emails with attachments and sizes in `backend/tests/mail_factory.py`, `download_attachment` and `download_attachment_response` in `backend/tests/factories.py`; the SPA harness answers for the download in `frontend/src/test/` — check — the tests of 1.2, 1.3 and 1.5 use them.
- [x] 1.5 SPA tests (`App.attachments.test.tsx`): «договор.pdf · PDF · 1,2 МБ», «смета.xlsx · XLSX · 812 Б», «README · 44 КБ», «акт.pdf · PDF»; a click saves the blob under its name; each error message shown under its attachment only — check — red against the current code.

## 2. Backend (code-writer)

- [x] 2.1 Migration `0009_email_attachments`: `emails.attachments` JSONB from `attachment_names` with null sizes, `attachment_names` dropped; downgrade restores it — check — `test_migrations.py` upgrade and downgrade pass.
- [x] 2.2 Parsing keeps names and decoded sizes through one attachment-list function; `EmailView.attachments` — check — tests 1.1 and 1.3 pass.
- [x] 2.3 `MailReader.fetch_message` in `platform/mail_reader.py` and the fake reader — check — tests 1.1 pass.
- [x] 2.4 Module `attachments`: router `GET /api/v1/emails/{email_id}/attachments/{index}`, the service picking copies by D4 through `correspondence.service` and `mailboxes.service`, the errors and headers of the interface — check — tests 1.2 pass; `just api-client` regenerates the client with no diff after a second run.

- [x] 2.5 Demo mail (`scripts/demo_mail.py`): two emails carry attachments — a small PDF «договор.pdf» and an «смета.xlsx» — so the manual flow has files to download — check — `just demo-mail` loads them and `just demo-mail status` counts them.

## 3. SPA (code-writer)

- [x] 3.1 `ChainPage.tsx`: the attachment list with type and size formatted by D7, download through the generated client and an object URL, the error under the clicked attachment — check — tests 1.5 pass, the page reads at 360 px in both themes.

## 4. Docs

- [x] 4.1 `docs/domain.md`: the note on data kept (attachment content fetched on click, never stored), the requirements map (FR-57, FR-58), `Last FR number: FR-58`, edition bump — check — `just check` passes the doc links and facts.

## 5. Verification

- [x] 5.1 `just check` — check — passes with no warnings.
- [x] 5.2 `/test` all — check — unit and database tests pass.
- [x] 5.3 Manual flow by `flow-checker` on the demo mail with an email carrying a PDF: open the chain, see name, type and size, download it and compare the size, see it still unread in GreenMail; disconnect the mailbox and see «Файл недоступен: ящик отключён» — check — every step PASS.

## 6. Done when (plan task 1.11)

- [x] 6.1 On the page of a chain every attachment of an email shows its name, type and size.
- [x] 6.2 A click on an attachment downloads the file under its name, the same as in the mailbox.
- [x] 6.3 After the download the email stays unread and unchanged in the mailbox.
- [x] 6.4 Attachments of emails read before this task download too, without a size.
- [x] 6.5 When no connected mailbox holds the email, the click shows «Файл недоступен: ящик отключён».
- [x] 6.6 When the email is gone from the mailbox, the click shows «Письмо больше не найдено в ящике».
- [x] 6.7 An attachment of another user's email answers «not found».
- [x] 6.8 `just check` and `just test-all` pass.
