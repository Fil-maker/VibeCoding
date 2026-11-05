# Spec Delta

## MODIFIED Requirements

### Requirement: FR-25 Reading never changes the mailbox

Reading a mailbox and fetching an attachment from it SHALL open every folder read-only. Neither SHALL
mark an email as read, set or clear any flag, move, copy, delete or send an email in the mailbox.

#### Scenario: Unread emails stay unread
- **WHEN** Анна's Inbox holds 3 unread emails and the app reads the mailbox
- **THEN** the 3 emails are in the app and all 3 stay unread in the mailbox, and the mailbox holds the same emails in the same folders as before

#### Scenario: Downloading an attachment keeps the email unread
- **WHEN** an unread email with «договор.pdf» is in Анна's Inbox and she downloads «договор.pdf» in the app
- **THEN** the email stays unread with the same flags in the same folder of the mailbox
