"""Use cases of mailboxes: connect, list, refresh, disconnect, and the background reading run."""

import asyncio
from dataclasses import dataclass
from datetime import timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.correspondence.service import store_raw_messages
from app.modules.mailboxes import repository
from app.modules.mailboxes.domain import describe_status_error
from app.modules.mailboxes.errors import (
    MailboxExists,
    MailboxServerUnreachable,
    MailboxSignInRefused,
)
from app.modules.mailboxes.models import Mailbox as MailboxRow
from app.modules.mailboxes.models import MailboxErrorCode, MailboxStatus
from app.modules.mailboxes.schemas import Mailbox, MailboxConnect
from app.platform.auth_context import AuthContext
from app.platform.clock import Clock
from app.platform.db import Database, get_database_session
from app.platform.errors import NotFound
from app.platform.logging import get_logger
from app.platform.mail_reader import (
    BATCH_SIZE,
    FolderKind,
    ImapCredentials,
    MailboxSignInFailed,
    MailboxUnreachable,
    MailReader,
)
from app.platform.secret_box import SecretBox, SecretBoxError
from app.platform.settings import Settings

LOG = get_logger(__name__)

# A `reading` status this old means the run died (a restart mid-read); the mailbox is due again.
ABANDONED_READING_MINUTES = 15


def to_mailbox_view(row: MailboxRow) -> Mailbox:
    """The API form of a mailbox row; it has no password."""
    return Mailbox(
        id=row.id,
        server=row.server,
        port=row.port,
        login=row.login,
        status=MailboxStatus(row.status),
        error=describe_status_error(row.status, row.error_code),
        last_read_at=row.last_read_at,
    )


def _use_tls(settings: Settings, server: str) -> bool:
    return server.lower() not in settings.insecure_hosts


async def _check_credentials(reader: MailReader, settings: Settings, body: MailboxConnect) -> None:
    credentials = ImapCredentials(
        server=body.server,
        port=body.port,
        login=body.login,
        password=body.password,
        use_tls=_use_tls(settings, body.server),
    )
    try:
        await reader.check(credentials)
    except MailboxSignInFailed as e:
        raise MailboxSignInRefused from e
    except MailboxUnreachable as e:
        raise MailboxServerUnreachable(body.server) from e


class MailboxesService:
    """The user-facing use cases of mailboxes bound to one database session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_mailboxes(self, context: AuthContext) -> list[Mailbox]:
        """The user's connected mailboxes by login."""
        async with self._session.begin():
            rows = await repository.list_connected_for_owner(self._session, context.user_id)
        return [to_mailbox_view(row) for row in rows]

    async def connect(
        self,
        context: AuthContext,
        reader: MailReader,
        secret_box: SecretBox,
        clock: Clock,
        settings: Settings,
        body: MailboxConnect,
    ) -> Mailbox:
        """Check the sign-in outside any transaction, then save; a failed check saves nothing.

        A disconnected mailbox of the same server and login is reused, so its folders keep
        their `last_uid` and no email is read twice (FR-27).
        """
        async with self._session.begin():
            known = await repository.get_by_server_and_login_for_owner(
                self._session, context.user_id, body.server, body.login
            )
            if known is not None and known.disconnected_at is None:
                raise MailboxExists
        await _check_credentials(reader, settings, body)
        encrypted = secret_box.encrypt(body.password)
        now = clock.now()
        try:
            async with self._session.begin():
                row = await repository.get_by_server_and_login_for_owner(
                    self._session, context.user_id, body.server, body.login
                )
                if row is None:
                    row = await repository.add_mailbox_for_owner(
                        self._session,
                        context.user_id,
                        server=body.server,
                        port=body.port,
                        login=body.login,
                        password_encrypted=encrypted,
                        now=now,
                    )
                elif row.disconnected_at is None:
                    raise MailboxExists
                else:
                    row.port = body.port
                    row.password_encrypted = encrypted
                    row.status = MailboxStatus.PENDING
                    row.error_code = None
                    row.read_requested_at = now
                    row.connected_at = now
                    row.disconnected_at = None
        except IntegrityError as e:
            if isinstance(e.orig, UniqueViolation):
                raise MailboxExists from e
            raise
        return to_mailbox_view(row)

    async def refresh(self, context: AuthContext, mailbox_id: UUID, clock: Clock) -> Mailbox:
        """Ask for a read at the next tick; a read in progress keeps its status."""
        async with self._session.begin():
            row = await repository.get_connected_by_id_for_owner(
                self._session, context.user_id, mailbox_id
            )
            if row is None:
                raise NotFound
            row.read_requested_at = clock.now()
            if row.status != MailboxStatus.READING:
                row.status = MailboxStatus.PENDING
                row.error_code = None
        return to_mailbox_view(row)

    async def disconnect(self, context: AuthContext, mailbox_id: UUID, clock: Clock) -> None:
        """Delete the password and stop reading; the rows and the emails stay."""
        async with self._session.begin():
            row = await repository.get_connected_by_id_for_owner(
                self._session, context.user_id, mailbox_id
            )
            if row is None:
                raise NotFound
            row.password_encrypted = None
            row.read_requested_at = None
            row.disconnected_at = clock.now()


def get_mailboxes_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> MailboxesService:
    """Dependency factory of the mailboxes use cases."""
    return MailboxesService(session)


@dataclass(frozen=True)
class _FolderProgress:
    id: UUID
    kind: FolderKind
    uidvalidity: int | None
    last_uid: int | None


@dataclass(frozen=True)
class _ReadJob:
    """What a claimed mailbox needs for a read; a snapshot, so no session is held."""

    mailbox_id: UUID
    user_id: UUID
    server: str
    port: int
    login: str
    password_encrypted: bytes
    folders: list[_FolderProgress]


async def _claim(
    database: Database, clock: Clock, settings: Settings, skip_ids: set[UUID]
) -> _ReadJob | None:
    """Lock one due mailbox in a short transaction and mark it `reading`."""
    now = clock.now()
    async with database.session() as session, session.begin():
        row = await repository.claim_next_due_mailbox(
            session,
            now=now,
            interval=timedelta(minutes=settings.mailbox_read_interval_minutes),
            abandoned_after=timedelta(minutes=ABANDONED_READING_MINUTES),
            skip_ids=skip_ids,
        )
        if row is None or row.password_encrypted is None:
            return None
        folders = await repository.ensure_folders(session, row.id)
        await repository.record_attempt_start(session, row.id, row.user_id, now=now)
        return _ReadJob(
            mailbox_id=row.id,
            user_id=row.user_id,
            server=row.server,
            port=row.port,
            login=row.login,
            password_encrypted=row.password_encrypted,
            folders=[
                _FolderProgress(f.id, FolderKind(f.kind), f.uidvalidity, f.last_uid)
                for f in folders
            ],
        )


async def _read_folder(
    database: Database,
    reader: MailReader,
    clock: Clock,
    settings: Settings,
    job: _ReadJob,
    credentials: ImapCredentials,
    folder: _FolderProgress,
) -> None:
    """Read a folder batch by batch, each batch stored in its own transaction."""
    since = clock.now().date() - timedelta(days=settings.mailbox_read_depth_days)
    uidvalidity, last_uid = folder.uidvalidity, folder.last_uid
    while True:
        batch = await reader.fetch(credentials, folder.kind, since, last_uid, uidvalidity)
        if batch.uidvalidity is None:
            return  # the folder does not exist on this server
        # A changed uidvalidity means the server restarted the read from `since`.
        restarted = batch.uidvalidity != uidvalidity
        previous = None if restarted else last_uid
        newest = max((m.uid for m in batch.messages), default=None)
        if newest is None:
            new_last = previous
        else:
            new_last = newest if previous is None else max(previous, newest)
        async with database.session() as session, session.begin():
            if batch.messages:
                await store_raw_messages(
                    session,
                    user_id=job.user_id,
                    mailbox_id=job.mailbox_id,
                    folder_id=folder.id,
                    uidvalidity=batch.uidvalidity,
                    messages=batch.messages,
                    now=clock.now(),
                )
            await repository.update_folder_progress(
                session,
                job.mailbox_id,
                folder.id,
                uidvalidity=batch.uidvalidity,
                last_uid=new_last,
            )
        stuck = not restarted and new_last == last_uid
        uidvalidity, last_uid = batch.uidvalidity, new_last
        if len(batch.messages) < BATCH_SIZE or stuck:
            return


def _error_code_of(error: Exception) -> MailboxErrorCode:
    if isinstance(error, MailboxSignInFailed | SecretBoxError):
        return MailboxErrorCode.SIGN_IN_FAILED
    if isinstance(error, MailboxUnreachable):
        return MailboxErrorCode.UNREACHABLE
    return MailboxErrorCode.READ_FAILED


async def _read_mailbox(
    database: Database, reader: MailReader, clock: Clock, settings: Settings, job: _ReadJob
) -> bool:
    """Read both folders of a claimed mailbox and record the outcome; True when it succeeded."""
    try:
        password = SecretBox(settings.mailbox_encryption_key).decrypt(job.password_encrypted)
        credentials = ImapCredentials(
            server=job.server,
            port=job.port,
            login=job.login,
            password=password,
            use_tls=_use_tls(settings, job.server),
        )
        for folder in job.folders:
            await _read_folder(database, reader, clock, settings, job, credentials, folder)
    except Exception as e:  # any failure of one mailbox is recorded and the run goes on
        code = _error_code_of(e)
        # The class name only: messages of mail libraries may carry addresses.
        LOG.warning("reading mailbox %s failed: %s (%s)", job.mailbox_id, code, type(e).__name__)
        async with database.session() as session, session.begin():
            await repository.record_read_failure(
                session, job.mailbox_id, job.user_id, error_code=code
            )
        return False
    async with database.session() as session, session.begin():
        await repository.record_read_success(session, job.mailbox_id, job.user_id, now=clock.now())
    return True


async def read_due_mailboxes(
    database: Database, reader: MailReader, clock: Clock, settings: Settings
) -> int:
    """Read every due mailbox once, one by one; return how many were read successfully."""
    done: set[UUID] = set()
    succeeded = 0
    while True:
        job = await _claim(database, clock, settings, done)
        if job is None:
            return succeeded
        done.add(job.mailbox_id)
        if await _read_mailbox(database, reader, clock, settings, job):
            succeeded += 1


async def run_reading_loop(
    database: Database, reader: MailReader, clock: Clock, settings: Settings
) -> None:
    """Look for due mailboxes every tick until cancelled; an error is logged, never fatal."""
    while True:
        try:
            await read_due_mailboxes(database, reader, clock, settings)
        except Exception:  # the loop must survive any failed run; the next tick retries
            LOG.exception("the mailbox reading run failed")
        await asyncio.sleep(settings.mailbox_read_tick_seconds)
