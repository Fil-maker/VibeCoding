"""Use case of attachments: fetch one attachment from a connected mailbox and keep nothing."""

from dataclasses import dataclass
from uuid import UUID

from app.modules.attachments.errors import (
    AttachmentEmailGone,
    AttachmentMailboxDisconnected,
    AttachmentServerUnreachable,
    AttachmentSignInFailed,
)
from app.modules.correspondence.domain import read_attachment
from app.modules.correspondence.service import get_attachment_target
from app.modules.mailboxes.service import MessageSource, list_message_sources
from app.platform.auth_context import AuthContext
from app.platform.db import Database
from app.platform.mail_reader import (
    MailboxReadFailed,
    MailboxSignInFailed,
    MailboxUnreachable,
    MailReader,
)
from app.platform.secret_box import SecretBox
from app.platform.settings import Settings


@dataclass(frozen=True)
class AttachmentFile:
    """A fetched attachment: its name and bytes, held in memory for one request."""

    name: str
    content: bytes


async def download_attachment(
    database: Database,
    reader: MailReader,
    settings: Settings,
    secret_box: SecretBox,
    context: AuthContext,
    email_id: UUID,
    index: int,
) -> AttachmentFile:
    """Fetch attachment `index` of the user's email from the first connected copy that has it.

    Inbox copies come before Sent ones, the oldest mailbox first (see `list_message_sources`).
    Nothing is written: a failed download leaves every mailbox status as it was.
    `NotFound` before any connection for another user's or an unknown email or a bad index.
    """
    async with database.session() as session, session.begin():
        target = await get_attachment_target(session, context.user_id, email_id, index)
        sources = await list_message_sources(
            session, context.user_id, target.copies, settings, secret_box
        )
    if not sources:
        raise AttachmentMailboxDisconnected
    failure: Exception | None = None
    for source in sources:
        try:
            content = await _read_from(reader, source, index, target.name)
        except (MailboxSignInFailed, MailboxUnreachable, MailboxReadFailed) as e:
            failure = e
            continue
        if content is not None:
            return AttachmentFile(target.name, content)
    if isinstance(failure, MailboxSignInFailed):
        raise AttachmentSignInFailed from failure
    if failure is not None:
        raise AttachmentServerUnreachable from failure
    raise AttachmentEmailGone


async def _read_from(
    reader: MailReader, source: MessageSource, index: int, name: str
) -> bytes | None:
    """The attachment from one copy; `None` when the copy is gone or is not this email."""
    raw = await reader.fetch_message(
        source.credentials, source.folder_name, source.uidvalidity, source.uid
    )
    return None if raw is None else read_attachment(raw, index, name)
