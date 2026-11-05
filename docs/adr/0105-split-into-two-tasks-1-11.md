# Split into two tasks: 1.11 attachments, 1.12 email rendering

Id: 0105 · Date: 05.11.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: 1.11.
- Task 1.11 adds attachment download: GET /api/v1/emails/{email_id}/attachments/{index} in the new backend module backend/app/modules/attachments (router.py, service.py, errors.py); it imports correspondence.service and mailboxes.service and is imported by neither.
- The download answers 200 with the bytes, Content-Type application/octet-stream, Content-Disposition attachment with filename*=UTF-8'' and the percent-encoded name, X-Content-Type-Options nosniff. Errors: 401 signed out; 404 another user's or unknown email, or index out of range, before any mailbox connection; 409 no connected mailbox holds a copy (AttachmentMailboxDisconnected, «Файл недоступен: ящик отключён»); 410 every connected copy gone (AttachmentEmailGone, «Письмо больше не найдено в ящике»); 502 sign-in refused (AttachmentSignInFailed); 504 server unreachable or refused to read (AttachmentServerUnreachable).
- Copy order (design D4): copies in connected mailboxes (password present, not disconnected), Inbox before Sent, then the mailbox's created_at, then UID; the first copy that yields the attachment wins; otherwise the error of the last tried copy. A copy whose stored password cannot be decrypted is skipped with a warning log naming the mailbox id. A failed download writes nothing, so the mailbox status stays as it was. The database transaction closes before any IMAP connection.
- The attachment content is fetched on each click and never stored; the whole message is fetched in memory for the request only.
- MailReader.fetch_message(credentials, folder_name, uidvalidity, uid) -> bytes | None: SELECT read-only, compares UIDVALIDITY, UID FETCH <uid> (BODY.PEEK[]); None means gone (changed UIDVALIDITY, missing folder, empty answer); a FETCH status other than OK raises MailboxReadFailed. The fake reader FakeMailReader has public remove, clear and replace for tests.
- An attachment is identified by its index in the email's attachment list in walk() order (design D2); on download, the part at that index must have the stored name, otherwise the copy is treated as not this email. Parsing keeps the name and the decoded size through one attachment-list function; a part without a file name is not an attachment.
- Migration 0009_email_attachments replaces emails.attachment_names (array) with emails.attachments JSONB: a list of {name, size}; emails read before get their names with size null; downgrade restores attachment_names.
- The chain API (EmailView) now returns attachments: a list of {index, name, size|null} instead of attachment_names.
- SPA: ChainPage shows each attachment through AttachmentButton (frontend/src/features/correspondence/AttachmentButton.tsx) as «name · EXT · size» (size formatted in format.ts: Б, КБ, МБ with a comma decimal; no size when null; no type when the name has no extension); a click downloads through the generated client into a Blob and an object URL saved under the attachment name; an error message is shown under the clicked attachment only.
- SPA test harness frontend/src/test/attachments.tsx answers the download request in tests.
- scripts/demo_mail.py: two demo emails carry attachments, «договор.pdf» (a small PDF) and «смета.xlsx», in the chain «Смета на ремонт офиса», so the manual flow has files to download.

## Decision
Split into two tasks: 1.11 attachments, 1.12 email rendering

## Alternatives
one task

## Reason
User chose «Две задачи»
