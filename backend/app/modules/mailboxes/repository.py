"""Named queries over mailboxes. Every query is owner-scoped unless its docstring says otherwise."""

from collections.abc import Collection
from datetime import datetime, timedelta
from uuid import UUID

from sqlalchemy import and_, or_, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.mailboxes.models import Mailbox, MailboxFolder, MailboxStatus
from app.platform.mail_reader import FolderKind

FOLDER_NAMES: dict[FolderKind, str] = {FolderKind.INBOX: "INBOX", FolderKind.SENT: "Sent"}

# A person has a handful of mailboxes; the cap only keeps the unpaginated list bounded.
MAILBOX_LIST_LIMIT = 100


async def list_logins_for_owner(session: AsyncSession, user_id: UUID) -> list[str]:
    """The logins of all of the user's mailboxes, connected or not (their own addresses)."""
    rows = await session.execute(select(Mailbox.login).where(Mailbox.user_id == user_id))
    return list(rows.scalars())


async def list_connected_for_owner(session: AsyncSession, user_id: UUID) -> list[Mailbox]:
    """The user's connected mailboxes by login, at most `MAILBOX_LIST_LIMIT` of them."""
    rows = await session.execute(
        select(Mailbox)
        .where(Mailbox.user_id == user_id, Mailbox.disconnected_at.is_(None))
        .order_by(Mailbox.login, Mailbox.id)
        .limit(MAILBOX_LIST_LIMIT)
    )
    return list(rows.scalars())


async def get_connected_by_id_for_owner(
    session: AsyncSession, user_id: UUID, mailbox_id: UUID
) -> Mailbox | None:
    """A connected mailbox of the user, row-locked; `None` if foreign or disconnected."""
    rows = await session.execute(
        select(Mailbox)
        .where(
            Mailbox.id == mailbox_id,
            Mailbox.user_id == user_id,
            Mailbox.disconnected_at.is_(None),
        )
        .with_for_update()
    )
    return rows.scalar_one_or_none()


async def get_by_server_and_login_for_owner(
    session: AsyncSession, user_id: UUID, server: str, login: str
) -> Mailbox | None:
    """The user's mailbox of this server and login, connected or not, row-locked."""
    rows = await session.execute(
        select(Mailbox)
        .where(Mailbox.user_id == user_id, Mailbox.server == server, Mailbox.login == login)
        .with_for_update()
    )
    return rows.scalar_one_or_none()


async def add_mailbox_for_owner(
    session: AsyncSession,
    user_id: UUID,
    *,
    server: str,
    port: int,
    login: str,
    password_encrypted: bytes,
    now: datetime,
) -> Mailbox:
    """Insert a pending mailbox that asks for its first read; the flush surfaces a duplicate."""
    mailbox = Mailbox(
        user_id=user_id,
        server=server,
        port=port,
        login=login,
        password_encrypted=password_encrypted,
        status=MailboxStatus.PENDING,
        read_requested_at=now,
        connected_at=now,
        created_at=now,
    )
    session.add(mailbox)
    await session.flush()
    return mailbox


async def claim_next_due_mailbox(
    session: AsyncSession,
    *,
    now: datetime,
    interval: timedelta,
    abandoned_after: timedelta,
    skip_ids: Collection[UUID],
) -> Mailbox | None:
    """Installation-wide (the background run serves every user): lock one due mailbox.

    Due: connected with a password, and either not `reading` and (a read was requested, or never
    tried, or the last attempt is `interval` old or older), or `reading` for `abandoned_after`.
    Rows locked by another run are skipped.
    """
    idle_and_due = and_(
        Mailbox.status != MailboxStatus.READING,
        or_(
            Mailbox.read_requested_at.is_not(None),
            Mailbox.last_attempt_at.is_(None),
            Mailbox.last_attempt_at <= now - interval,
        ),
    )
    abandoned = and_(
        Mailbox.status == MailboxStatus.READING,
        or_(Mailbox.last_attempt_at.is_(None), Mailbox.last_attempt_at <= now - abandoned_after),
    )
    rows = await session.execute(
        select(Mailbox)
        .where(
            Mailbox.disconnected_at.is_(None),
            Mailbox.password_encrypted.is_not(None),
            or_(idle_and_due, abandoned),
            Mailbox.id.not_in(skip_ids),
        )
        .order_by(Mailbox.created_at, Mailbox.id)
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    return rows.scalar_one_or_none()


async def ensure_folders(session: AsyncSession, mailbox_id: UUID) -> list[MailboxFolder]:
    """The inbox and sent rows of a mailbox, created on the first read.

    Not owner-filtered: the background run calls it for a mailbox it has just claimed.
    """
    rows = await session.execute(
        select(MailboxFolder).where(MailboxFolder.mailbox_id == mailbox_id)
    )
    folders = {FolderKind(folder.kind): folder for folder in rows.scalars()}
    for kind, name in FOLDER_NAMES.items():
        if kind not in folders:
            folder = MailboxFolder(mailbox_id=mailbox_id, kind=kind, name=name)
            session.add(folder)
            folders[kind] = folder
    await session.flush()
    return [folders[kind] for kind in FOLDER_NAMES]


async def update_folder_progress(
    session: AsyncSession,
    mailbox_id: UUID,
    folder_id: UUID,
    *,
    uidvalidity: int,
    last_uid: int | None,
) -> None:
    """Record how far a folder has been read.

    Not owner-filtered: the folder id comes from the mailbox the background run has claimed.
    """
    await session.execute(
        update(MailboxFolder)
        .where(MailboxFolder.id == folder_id, MailboxFolder.mailbox_id == mailbox_id)
        .values(uidvalidity=uidvalidity, last_uid=last_uid)
    )


async def record_attempt_start(
    session: AsyncSession, mailbox_id: UUID, user_id: UUID, *, now: datetime
) -> None:
    """Mark a claimed mailbox as being read; a request made from now on asks for another read."""
    await session.execute(
        update(Mailbox)
        .where(Mailbox.id == mailbox_id, Mailbox.user_id == user_id)
        .values(
            status=MailboxStatus.READING,
            error_code=None,
            last_attempt_at=now,
            read_requested_at=None,
        )
    )


async def record_read_success(
    session: AsyncSession, mailbox_id: UUID, user_id: UUID, *, now: datetime
) -> None:
    """Mark a mailbox as read."""
    await session.execute(
        update(Mailbox)
        .where(Mailbox.id == mailbox_id, Mailbox.user_id == user_id)
        .values(status=MailboxStatus.READ, error_code=None, last_read_at=now)
    )


async def record_read_failure(
    session: AsyncSession, mailbox_id: UUID, user_id: UUID, *, error_code: str
) -> None:
    """Mark a mailbox as failed with the reason; emails already stored stay."""
    await session.execute(
        update(Mailbox)
        .where(Mailbox.id == mailbox_id, Mailbox.user_id == user_id)
        .values(status=MailboxStatus.FAILED, error_code=error_code)
    )
