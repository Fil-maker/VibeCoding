"""Reading a user's mailbox: a protocol, the IMAP reader and a fake for tests.

The reader only reads. It sends `LOGIN`, `LIST`, a read-only `SELECT`, `UID SEARCH`, `UID FETCH`
with `BODY.PEEK[]` and `LOGOUT`, and no command that writes to the server (FR-25).
"""

import asyncio
import imaplib
import re
import ssl
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import UTC, date, datetime
from email.parser import BytesParser
from email.utils import parsedate_to_datetime
from enum import StrEnum
from typing import Protocol

from fastapi import Request

from app.platform.imap_folders import find_sent_folder, parse_list_response, quote_mailbox
from app.platform.settings import Settings

BATCH_SIZE = 50
INBOX_NAME = "INBOX"
FAKE_UIDVALIDITY = 1
FETCH_PAIR = 2
MONTHS = ("Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec")

ImapConnect = Callable[[str, int, bool, float], imaplib.IMAP4]


class FolderKind(StrEnum):
    """The folders the app reads."""

    INBOX = "inbox"
    SENT = "sent"


class MailboxSignInFailed(Exception):
    """The server refused the login or the password."""


class MailboxUnreachable(Exception):
    """The server did not answer, or the connection broke."""


class MailboxReadFailed(Exception):
    """The server answered, but a folder could not be read."""


@dataclass(frozen=True)
class ImapCredentials:
    """Where and how to sign in; the password lives only in memory."""

    server: str
    port: int
    login: str
    password: str = field(repr=False)
    use_tls: bool = True


@dataclass(frozen=True)
class RawMessage:
    """One message as the server holds it."""

    uid: int
    data: bytes
    internal_date: datetime


@dataclass(frozen=True)
class FolderBatch:
    """Up to `BATCH_SIZE` messages of a folder, lowest UIDs first, all above the asked `after_uid`.

    `uidvalidity` is the server's current one; `None` when the folder does not exist. When it
    differs from the asked one, `after_uid` was ignored and the read restarted from `since`.
    An empty `messages` means nothing is left; fewer than `BATCH_SIZE` also means the end.
    """

    uidvalidity: int | None
    messages: list[RawMessage]


class MailReader(Protocol):
    """Checks a login and reads folders; nothing here changes a mailbox."""

    async def check(self, credentials: ImapCredentials) -> None:
        """Sign in and out; raise `MailboxSignInFailed` or `MailboxUnreachable`."""
        ...

    async def fetch(
        self,
        credentials: ImapCredentials,
        folder: FolderKind,
        since: date,
        after_uid: int | None,
        uidvalidity: int | None,
    ) -> FolderBatch:
        """The next batch of a folder: messages of `since` or later with a UID above `after_uid`."""
        ...


def _default_connect(server: str, port: int, use_tls: bool, timeout: float) -> imaplib.IMAP4:
    if use_tls:
        return imaplib.IMAP4_SSL(
            server, port, ssl_context=ssl.create_default_context(), timeout=timeout
        )
    return imaplib.IMAP4(server, port, timeout=timeout)


def _imap_date(day: date) -> str:
    return f"{day.day:02d}-{MONTHS[day.month - 1]}-{day.year}"


_UID = re.compile(rb"\bUID (\d+)")
_INTERNAL_DATE = re.compile(rb'INTERNALDATE "([^"]+)"')


def _internal_date(meta: bytes) -> datetime:
    found = _INTERNAL_DATE.search(meta)
    if found is not None:
        try:
            parsed = parsedate_to_datetime(found.group(1).decode("ascii").strip())
        except (ValueError, TypeError):
            parsed = None
        if parsed is not None and parsed.tzinfo is not None:
            return parsed.astimezone(UTC)
    return datetime.fromtimestamp(0, UTC)


def _parse_fetch(items: list[object]) -> list[RawMessage]:
    messages: list[RawMessage] = []
    for index, item in enumerate(items):
        if not isinstance(item, tuple) or len(item) != FETCH_PAIR:  # pyright: ignore[reportUnknownArgumentType] -- imaplib types items as Any
            continue
        head, body = item  # pyright: ignore[reportUnknownVariableType] -- see above
        tail = items[index + 1] if index + 1 < len(items) else b""
        meta = (head if isinstance(head, bytes) else b"") + (
            tail if isinstance(tail, bytes) else b""
        )
        uid = _UID.search(meta)
        if uid is not None and isinstance(body, bytes):
            messages.append(RawMessage(int(uid.group(1)), body, _internal_date(meta)))
    return sorted(messages, key=lambda message: message.uid)


class ImapMailReader:
    """Reads over IMAP in a worker thread; the connection comes from a factory so tests fake it."""

    def __init__(self, timeout: float, connect: ImapConnect = _default_connect) -> None:
        self._timeout = timeout
        self._connect = connect

    async def check(self, credentials: ImapCredentials) -> None:
        """Sign in and out; see `MailReader.check`."""
        await asyncio.to_thread(self._check, credentials)

    async def fetch(
        self,
        credentials: ImapCredentials,
        folder: FolderKind,
        since: date,
        after_uid: int | None,
        uidvalidity: int | None,
    ) -> FolderBatch:
        """The next batch of a folder; see `MailReader.fetch`."""
        return await asyncio.to_thread(
            self._fetch, credentials, folder, since, after_uid, uidvalidity
        )

    def _open(self, credentials: ImapCredentials) -> imaplib.IMAP4:
        try:
            connection = self._connect(
                credentials.server, credentials.port, credentials.use_tls, self._timeout
            )
        except (OSError, imaplib.IMAP4.error) as e:
            raise MailboxUnreachable("the server did not answer") from e
        try:
            connection.login(credentials.login, credentials.password)
        except imaplib.IMAP4.abort as e:
            self._close(connection)
            raise MailboxUnreachable("the connection broke at sign-in") from e
        except (imaplib.IMAP4.error, ValueError) as e:
            # ValueError: a password imaplib cannot encode is one the server cannot have accepted.
            self._close(connection)
            raise MailboxSignInFailed("the server refused the login") from e
        except OSError as e:
            self._close(connection)
            raise MailboxUnreachable("the connection broke at sign-in") from e
        return connection

    @staticmethod
    def _close(connection: imaplib.IMAP4) -> None:
        try:
            connection.logout()
        except (imaplib.IMAP4.error, OSError):
            return  # the connection is gone already; nothing is left to close

    def _check(self, credentials: ImapCredentials) -> None:
        self._close(self._open(credentials))

    def _fetch(
        self,
        credentials: ImapCredentials,
        folder: FolderKind,
        since: date,
        after_uid: int | None,
        uidvalidity: int | None,
    ) -> FolderBatch:
        connection = self._open(credentials)
        try:
            return self._read_folder(connection, folder, since, after_uid, uidvalidity)
        except imaplib.IMAP4.abort as e:
            raise MailboxUnreachable("the connection broke while reading") from e
        except imaplib.IMAP4.error as e:
            raise MailboxReadFailed("the server refused to read the folder") from e
        except OSError as e:
            raise MailboxUnreachable("the connection broke while reading") from e
        finally:
            self._close(connection)

    def _folder_name(self, connection: imaplib.IMAP4, folder: FolderKind) -> str | None:
        if folder is FolderKind.INBOX:
            return INBOX_NAME
        _status, data = connection.list()
        entry = find_sent_folder(parse_list_response(list(data)))  # pyright: ignore[reportArgumentType] -- LIST data is bytes lines or (head, literal) pairs
        return entry.name if entry is not None else None

    def _read_folder(
        self,
        connection: imaplib.IMAP4,
        folder: FolderKind,
        since: date,
        after_uid: int | None,
        uidvalidity: int | None,
    ) -> FolderBatch:
        name = self._folder_name(connection, folder)
        if name is None:
            return FolderBatch(uidvalidity=None, messages=[])
        connection.select(quote_mailbox(name), readonly=True)
        _code, values = connection.response("UIDVALIDITY")
        current = int(values[0]) if values and values[0] else None
        floor = after_uid if after_uid is not None and uidvalidity == current else None
        criteria = ["SINCE", _imap_date(since)]
        if floor is not None:
            criteria = ["UID", f"{floor + 1}:*", *criteria]
        _status, found = connection.uid("SEARCH", *criteria)
        raw = found[0] if found and found[0] else b""
        uids = sorted(int(part) for part in raw.split())
        # `n:*` always includes the highest message, even when it is below n.
        wanted = [uid for uid in uids if floor is None or uid > floor][:BATCH_SIZE]
        if not wanted:
            return FolderBatch(uidvalidity=current, messages=[])
        _status, items = connection.uid(
            "FETCH", ",".join(str(uid) for uid in wanted), "(BODY.PEEK[] FLAGS INTERNALDATE)"
        )
        return FolderBatch(uidvalidity=current, messages=_parse_fetch(list(items)))


# The fake dates messages without a parsable Date header with this fixed moment.
FAKE_UNDATED_MESSAGE_DATE = datetime(2026, 1, 1, tzinfo=UTC)


@dataclass
class _StoredMessage:
    uid: int
    data: bytes
    internal_date: datetime
    seen: bool


@dataclass
class FakeMailReader:
    """An in-memory mail server keyed by login; reading never changes a flag."""

    _folders: dict[tuple[str, FolderKind], list[_StoredMessage]] = field(default_factory=lambda: {})
    _sign_in_failures: set[str] = field(default_factory=set[str])
    _unreachable: set[str] = field(default_factory=set[str])

    def add(
        self,
        login: str,
        folder: FolderKind,
        raw: bytes,
        *,
        seen: bool = False,
        internal_date: datetime | None = None,
    ) -> int:
        """Put a message in a folder and return its UID.

        The arrival date is `internal_date`, else the `Date` header, else the fixed
        `FAKE_UNDATED_MESSAGE_DATE`, so tests stay deterministic.
        """
        stored = self._folders.setdefault((login, folder), [])
        uid = max((message.uid for message in stored), default=0) + 1
        moment = internal_date if internal_date is not None else self._header_date(raw)
        stored.append(_StoredMessage(uid, raw, moment, seen))
        return uid

    @staticmethod
    def _header_date(raw: bytes) -> datetime:
        header = BytesParser().parsebytes(raw, headersonly=True).get("Date")
        if header is not None:
            try:
                parsed = parsedate_to_datetime(str(header))
            except (ValueError, TypeError):
                parsed = None
            if parsed is not None and parsed.tzinfo is not None:
                return parsed.astimezone(UTC)
        return FAKE_UNDATED_MESSAGE_DATE

    def seen_flags(self, login: str, folder: FolderKind) -> dict[int, bool]:
        """UID to whether the message is marked seen."""
        return {m.uid: m.seen for m in self._folders.get((login, folder), [])}

    def fail_sign_in(self, login: str) -> None:
        """From now on the server refuses this login."""
        self._sign_in_failures.add(login)

    def make_unreachable(self, server: str) -> None:
        """From now on this server does not answer."""
        self._unreachable.add(server)

    def restore(self, server: str) -> None:
        """The server answers again."""
        self._unreachable.discard(server)

    def _guard(self, credentials: ImapCredentials) -> None:
        if credentials.server in self._unreachable:
            raise MailboxUnreachable("the fake server does not answer")
        if credentials.login in self._sign_in_failures:
            raise MailboxSignInFailed("the fake server refused the login")

    async def check(self, credentials: ImapCredentials) -> None:
        """Fail like a server that is down or refuses the login, else pass."""
        self._guard(credentials)

    async def fetch(
        self,
        credentials: ImapCredentials,
        folder: FolderKind,
        since: date,
        after_uid: int | None,
        uidvalidity: int | None,
    ) -> FolderBatch:
        """The next batch, by the rules of `FolderBatch`; flags are left alone."""
        self._guard(credentials)
        floor = after_uid if after_uid is not None and uidvalidity == FAKE_UIDVALIDITY else None
        stored = sorted(self._folders.get((credentials.login, folder), []), key=lambda m: m.uid)
        chosen = [
            RawMessage(m.uid, m.data, m.internal_date)
            for m in stored
            if m.internal_date.date() >= since and (floor is None or m.uid > floor)
        ]
        return FolderBatch(uidvalidity=FAKE_UIDVALIDITY, messages=chosen[:BATCH_SIZE])


def get_mail_reader(request: Request) -> MailReader:
    """Dependency: the app's reader, created on first use; tests override it with the fake."""
    reader: MailReader | None = getattr(request.app.state, "mail_reader", None)
    if reader is None:
        settings: Settings = request.app.state.settings
        reader = ImapMailReader(timeout=settings.imap_timeout_seconds)
        request.app.state.mail_reader = reader
    return reader
