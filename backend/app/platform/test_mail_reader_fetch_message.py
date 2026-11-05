"""Unit tests of `fetch_message` of the IMAP reader on a recording connection (change 1-11)."""

import imaplib
import re

import pytest

from app.platform.mail_reader import MailboxReadFailed, MailboxSignInFailed, MailboxUnreachable
from app.platform.test_mail_reader import (
    ALLOWED,
    CREDENTIALS,
    RAW,
    RecordingConnection,
    reader_on,
)

SERVER_UIDVALIDITY = 7  # what RecordingConnection answers


async def test_fr25_fetching_a_message_sends_only_read_only_commands() -> None:
    # FR-25: an attachment is fetched with a read-only SELECT and BODY.PEEK[], nothing that writes
    connection = RecordingConnection()
    reader, _ = reader_on(connection)

    await reader.fetch_message(CREDENTIALS, "INBOX", SERVER_UIDVALIDITY, 101)

    assert connection.commands[0] == "LOGIN"
    assert connection.commands[-1] == "LOGOUT"
    assert all(command.startswith(ALLOWED) for command in connection.commands)
    selects = [c for c in connection.commands if c.startswith("SELECT")]
    assert selects == ["SELECT INBOX readonly=True"]
    fetches = [c for c in connection.commands if c.startswith("UID FETCH")]
    assert len(fetches) == 1
    assert re.fullmatch(r"UID FETCH 101 \(BODY\.PEEK\[\][^)]*\)", fetches[0])
    assert "BODY[" not in fetches[0].replace("BODY.PEEK[", "")
    for writing in ("STORE", "COPY", "MOVE", "EXPUNGE", "APPEND"):
        assert not any(writing in command for command in connection.commands)
    assert connection.forbidden == []


async def test_fetching_a_message_opens_the_folder_by_the_stored_server_name() -> None:
    # design D3: SELECT of the folder by its stored server name
    connection = RecordingConnection()
    reader, _ = reader_on(connection)

    await reader.fetch_message(CREDENTIALS, "Gesendet", SERVER_UIDVALIDITY, 101)

    selects = [c for c in connection.commands if c.startswith("SELECT")]
    assert selects == ["SELECT Gesendet readonly=True"]


async def test_fetching_a_message_of_a_changed_uidvalidity_asks_for_no_message() -> None:
    # design D3: a changed UIDVALIDITY means the stored UID points to another message (gone)
    connection = RecordingConnection()
    reader, _ = reader_on(connection)

    await reader.fetch_message(CREDENTIALS, "INBOX", SERVER_UIDVALIDITY + 1, 101)

    assert [c for c in connection.commands if c.startswith("UID FETCH")] == []
    assert connection.commands[-1] == "LOGOUT"
    assert connection.forbidden == []


async def test_fetching_a_message_with_a_refused_login_is_a_sign_in_failure() -> None:
    # FR-58 «The server refuses the sign-in»
    error = imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials")
    reader, _ = reader_on(RecordingConnection(login_error=error))

    with pytest.raises(MailboxSignInFailed):
        await reader.fetch_message(CREDENTIALS, "INBOX", SERVER_UIDVALIDITY, 101)


@pytest.mark.parametrize("command", ["SELECT", "FETCH"])
async def test_a_timeout_while_fetching_a_message_is_unreachable(command: str) -> None:
    # FR-58 «The server does not answer»
    connection = RecordingConnection()
    connection.error_on[command] = TimeoutError()
    reader, _ = reader_on(connection)

    with pytest.raises(MailboxUnreachable):
        await reader.fetch_message(CREDENTIALS, "INBOX", SERVER_UIDVALIDITY, 101)


async def test_a_refused_fetch_is_a_read_failure_not_a_gone_message() -> None:
    # FR-58: a NO answer to FETCH is a read failure, not «the message is gone»
    class RefusingFetch(RecordingConnection):
        def uid(self, command: str, *args: str) -> tuple[str, list[bytes]]:
            self.commands.append(f"UID {command.upper()} {' '.join(args)}")
            return "NO", [b"refused"]

    reader, _ = reader_on(RefusingFetch())

    with pytest.raises(MailboxReadFailed):
        await reader.fetch_message(CREDENTIALS, "INBOX", SERVER_UIDVALIDITY, 101)


async def test_fetching_a_message_returns_its_bytes() -> None:
    # design D3: the whole message by UID
    other = RAW + b"other message"
    connection = RecordingConnection(messages={101: RAW, 102: other})
    reader, _ = reader_on(connection)

    found = await reader.fetch_message(CREDENTIALS, "INBOX", SERVER_UIDVALIDITY, 102)
    first = await reader.fetch_message(CREDENTIALS, "INBOX", SERVER_UIDVALIDITY, 101)

    assert found == other
    assert first == RAW


async def test_fetching_a_message_of_a_changed_uidvalidity_gives_none() -> None:
    # design D3: a changed UIDVALIDITY means the message is gone
    reader, _ = reader_on(RecordingConnection(messages={101: RAW}))

    gone = await reader.fetch_message(CREDENTIALS, "INBOX", SERVER_UIDVALIDITY + 1, 101)

    assert gone is None


async def test_fetching_a_message_with_an_empty_answer_gives_none() -> None:
    # design D3: an empty FETCH answer means the message is gone
    reader, _ = reader_on(RecordingConnection(messages={}))

    gone = await reader.fetch_message(CREDENTIALS, "INBOX", SERVER_UIDVALIDITY, 101)

    assert gone is None
