"""Unit tests of the mailbox reader: the IMAP reader on a recording connection, and the fake."""

import imaplib
from datetime import UTC, date, datetime
from typing import Any

import pytest

from app.platform.mail_reader import (
    FakeMailReader,
    FolderKind,
    ImapCredentials,
    ImapMailReader,
    MailboxSignInFailed,
    MailboxUnreachable,
    RawMessage,
)

INBOX = FolderKind("inbox")
SENT = FolderKind("sent")
CRLF = bytes([13, 10])
BACKSLASH = chr(92).encode()
RAW = b"Subject: Test" + CRLF + b"Message-ID: <t-1@stroy.test>" + CRLF + CRLF + b"Body" + CRLF
Reply = tuple[str, list[Any]]
ALLOWED = ("LOGIN", "LIST", "SELECT", "UID SEARCH", "UID FETCH", "LOGOUT")
CREDENTIALS = ImapCredentials(
    server="imap.yandex.ru",
    port=993,
    login="anna@yandex.ru",
    password="app-pass-1234",
    use_tls=True,
)
LIST_LINES = [
    b"(" + BACKSLASH + b'HasNoChildren) "/" "INBOX"',
    b"(" + BACKSLASH + b"HasNoChildren " + BACKSLASH + b'Sent) "/" "Gesendet"',
    b"(" + BACKSLASH + b'HasNoChildren) "/" "Trash"',
]


class RecordingConnection:
    """A fake IMAP connection that records every command and answers like a small server.

    Any method it does not define is recorded in `forbidden` and answers «OK».
    """

    def __init__(
        self,
        *,
        messages: dict[int, bytes] | None = None,
        login_error: Exception | None = None,
        list_error: Exception | None = None,
    ) -> None:
        self.messages = {101: RAW} if messages is None else messages
        self.login_error = login_error
        self.list_error = list_error
        self.error_on: dict[str, Exception] = {}
        self.commands: list[str] = []
        self.forbidden: list[str] = []
        self.untagged_responses: dict[str, list[bytes]] = {"UIDVALIDITY": [b"7"]}

    def login(self, user: str, password: str) -> Reply:
        self.commands.append("LOGIN")
        if self.login_error is not None:
            raise self.login_error
        return "OK", [b"logged in"]

    def list(self, directory: str = '""', pattern: str = "*") -> Reply:
        self.commands.append("LIST")
        if self.list_error is not None:
            raise self.list_error
        return "OK", LIST_LINES

    def select(self, mailbox: str = "INBOX", readonly: bool = False) -> Reply:
        self.commands.append(f"SELECT {mailbox.strip(chr(34))} readonly={readonly}")
        if "SELECT" in self.error_on:
            raise self.error_on["SELECT"]
        return "OK", [str(len(self.messages)).encode()]

    def response(self, code: str) -> Reply:
        return code, list(self.untagged_responses.get(code, []))

    def uid(self, command: str, *args: str) -> Reply:
        self.commands.append(f"UID {command.upper()} {' '.join(args)}")
        if command.upper() in self.error_on:
            raise self.error_on[command.upper()]
        if command.upper() == "SEARCH":
            return "OK", [b" ".join(str(uid).encode() for uid in self.messages)]
        data: list[Any] = []
        for index, (uid, raw) in enumerate(self.messages.items(), start=1):
            head = (
                f'{index} (UID {uid} FLAGS () INTERNALDATE "05-Jan-2099 10:30:00 +0000" '
                f"BODY[] {{{len(raw)}}}"
            ).encode()
            data.extend([(head, raw), b")"])
        return "OK", data

    def logout(self) -> Reply:
        self.commands.append("LOGOUT")
        return "BYE", [b"bye"]

    def __getattr__(self, name: str) -> Any:
        self.forbidden.append(name)

        def accept(*args: object, **kwargs: object) -> Reply:
            return "OK", []

        return accept


def reader_on(connection: RecordingConnection) -> tuple[ImapMailReader, list[tuple[Any, ...]]]:
    """An `ImapMailReader` whose connections are the given one; returns the connect calls too."""
    calls: list[tuple[Any, ...]] = []

    def connect(server: str, port: int, use_tls: bool, timeout: float) -> imaplib.IMAP4:
        calls.append((server, port, use_tls, timeout))
        return connection  # pyright: ignore[reportReturnType] -- the fake stands for IMAP4

    return ImapMailReader(timeout=12.5, connect=connect), calls


async def test_fr25_a_read_sends_only_read_only_commands() -> None:
    # FR-25: only LOGIN, LIST, read-only SELECT, UID SEARCH, UID FETCH with BODY.PEEK[], LOGOUT
    connection = RecordingConnection()
    reader, _ = reader_on(connection)

    await reader.fetch(CREDENTIALS, INBOX, date(2098, 1, 1), None, None)

    assert connection.commands[0] == "LOGIN"
    assert connection.commands[-1] == "LOGOUT"
    assert all(command.startswith(ALLOWED) for command in connection.commands)
    selects = [c for c in connection.commands if c.startswith("SELECT")]
    assert selects == ["SELECT INBOX readonly=True"]
    fetches = [c for c in connection.commands if c.startswith("UID FETCH")]
    assert fetches
    assert all("BODY.PEEK[" in c for c in fetches)
    assert all("BODY[" not in c.replace("BODY.PEEK[", "") for c in fetches)
    assert connection.forbidden == []


async def test_fr25_a_check_only_signs_in_and_out() -> None:
    # FR-25: checking the credentials issues no command that writes
    connection = RecordingConnection()
    reader, _ = reader_on(connection)

    await reader.check(CREDENTIALS)

    assert connection.commands[0] == "LOGIN"
    assert connection.commands[-1] == "LOGOUT"
    assert all(command.startswith(ALLOWED) for command in connection.commands)
    assert connection.forbidden == []


async def test_fetch_returns_the_raw_messages_with_uid_and_internal_date() -> None:
    # design «Interface»: FolderBatch with uidvalidity and RawMessage(uid, data, internal_date)
    connection = RecordingConnection(messages={101: RAW, 102: RAW + b"more" + CRLF})
    reader, _ = reader_on(connection)

    batch = await reader.fetch(CREDENTIALS, INBOX, date(2098, 1, 1), None, None)

    assert batch.uidvalidity == 7
    when = datetime(2099, 1, 5, 10, 30, tzinfo=UTC)
    assert batch.messages == [
        RawMessage(uid=101, data=RAW, internal_date=when),
        RawMessage(uid=102, data=RAW + b"more" + CRLF, internal_date=when),
    ]


async def test_fetch_asks_only_for_uids_after_the_last_one_and_since_the_date() -> None:
    # design «Folders and incremental reading»: UID SEARCH UID <last_uid+1>:* SINCE <date>
    connection = RecordingConnection()
    reader, _ = reader_on(connection)

    await reader.fetch(CREDENTIALS, INBOX, date(2098, 1, 1), 100, 7)

    [search] = [c for c in connection.commands if c.startswith("UID SEARCH")]
    assert "101:*" in search
    assert "SINCE 01-Jan-2098" in search


async def test_fetch_of_sent_opens_the_folder_marked_as_sent() -> None:
    # design «Folders»: Sent is the folder with the Sent special-use attribute
    connection = RecordingConnection()
    reader, _ = reader_on(connection)

    await reader.fetch(CREDENTIALS, SENT, date(2098, 1, 1), None, None)

    selects = [c for c in connection.commands if c.startswith("SELECT")]
    assert selects == ["SELECT Gesendet readonly=True"]


async def test_the_connection_gets_the_server_port_tls_flag_and_timeout() -> None:
    # design «IMAP client»: a socket timeout, TLS unless the host is a local test server
    reader, calls = reader_on(RecordingConnection())

    await reader.check(CREDENTIALS)

    assert calls == [("imap.yandex.ru", 993, True, 12.5)]


async def test_a_refused_login_is_a_sign_in_failure() -> None:
    # FR-22 «Wrong password»
    error = imaplib.IMAP4.error("[AUTHENTICATIONFAILED] Invalid credentials")
    reader, _ = reader_on(RecordingConnection(login_error=error))

    with pytest.raises(MailboxSignInFailed):
        await reader.check(CREDENTIALS)
    with pytest.raises(MailboxSignInFailed):
        await reader.fetch(CREDENTIALS, INBOX, date(2098, 1, 1), None, None)


@pytest.mark.parametrize("error", [TimeoutError(), ConnectionRefusedError(), OSError("no route")])
async def test_a_connection_that_cannot_be_opened_is_unreachable(error: Exception) -> None:
    # FR-22 «Unreachable server»
    def connect(server: str, port: int, use_tls: bool, timeout: float) -> imaplib.IMAP4:
        raise error

    reader = ImapMailReader(timeout=1.0, connect=connect)

    with pytest.raises(MailboxUnreachable):
        await reader.check(CREDENTIALS)
    with pytest.raises(MailboxUnreachable):
        await reader.fetch(CREDENTIALS, INBOX, date(2098, 1, 1), None, None)


@pytest.mark.parametrize("command", ["SELECT", "SEARCH", "FETCH"])
async def test_a_timeout_in_the_middle_of_a_read_is_unreachable(command: str) -> None:
    # FR-26 «The server is down for a while»: a timeout at any step of the read
    connection = RecordingConnection()
    connection.error_on[command] = TimeoutError()
    reader, _ = reader_on(connection)

    with pytest.raises(MailboxUnreachable):
        await reader.fetch(CREDENTIALS, INBOX, date(2098, 1, 1), None, None)


async def test_a_timeout_on_list_is_unreachable() -> None:
    # FR-26 «The server is down for a while»
    reader, _ = reader_on(RecordingConnection(list_error=TimeoutError()))

    with pytest.raises(MailboxUnreachable):
        await reader.fetch(CREDENTIALS, SENT, date(2098, 1, 1), None, None)


# --- FakeMailReader ---


async def test_the_fake_keeps_the_flags_on_fetch() -> None:
    # test double: the fake never changes a flag on fetch
    fake = FakeMailReader()
    unread = fake.add("anna@yandex.ru", INBOX, RAW, seen=False)
    read = fake.add("anna@yandex.ru", INBOX, RAW + b"x" + CRLF, seen=True)

    batch = await fake.fetch(CREDENTIALS, INBOX, date(2000, 1, 1), None, None)

    assert [m.uid for m in batch.messages] == [unread, read]
    assert fake.seen_flags("anna@yandex.ru", INBOX) == {unread: False, read: True}


async def test_the_fake_fetches_only_after_the_given_uid_from_the_right_folder() -> None:
    fake = FakeMailReader()
    first = fake.add("anna@yandex.ru", INBOX, RAW)
    second = fake.add("anna@yandex.ru", INBOX, RAW + b"x" + CRLF)
    fake.add("anna@yandex.ru", SENT, RAW + b"y" + CRLF)
    initial = await fake.fetch(CREDENTIALS, INBOX, date(2000, 1, 1), None, None)
    batch = await fake.fetch(CREDENTIALS, INBOX, date(2000, 1, 1), first, initial.uidvalidity)

    assert [m.uid for m in batch.messages] == [second]


async def test_the_fake_refuses_a_login_told_to_fail_and_a_server_made_unreachable() -> None:
    fake = FakeMailReader()
    fake.fail_sign_in("anna@yandex.ru")
    fake.make_unreachable("imap.yandex.ru")

    with pytest.raises(MailboxUnreachable):
        await fake.check(CREDENTIALS)
    fake.restore("imap.yandex.ru")
    with pytest.raises(MailboxSignInFailed):
        await fake.check(CREDENTIALS)
