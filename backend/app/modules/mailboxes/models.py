"""Tables of connected mailboxes and the folders read from them."""

from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    BigInteger,
    DateTime,
    ForeignKey,
    Integer,
    LargeBinary,
    String,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base

SERVER_MAX_LENGTH = 253
LOGIN_MAX_LENGTH = 254
STATUS_MAX_LENGTH = 20
KIND_MAX_LENGTH = 10
FOLDER_NAME_MAX_LENGTH = 255


class MailboxStatus(StrEnum):
    """Where a mailbox is in its reading cycle."""

    PENDING = "pending"
    READING = "reading"
    READ = "read"
    FAILED = "failed"


class MailboxErrorCode(StrEnum):
    """Why the last read failed."""

    SIGN_IN_FAILED = "sign_in_failed"
    UNREACHABLE = "unreachable"
    READ_FAILED = "read_failed"


class Mailbox(Base):
    """A mailbox of a user. Disconnecting keeps the row (its emails stay) and drops the password."""

    __tablename__ = "mailboxes"
    __table_args__ = (UniqueConstraint("user_id", "server", "login"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    server: Mapped[str] = mapped_column(String(SERVER_MAX_LENGTH))
    port: Mapped[int] = mapped_column(Integer)
    login: Mapped[str] = mapped_column(String(LOGIN_MAX_LENGTH))
    password_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    status: Mapped[str] = mapped_column(String(STATUS_MAX_LENGTH))
    error_code: Mapped[str | None] = mapped_column(String(STATUS_MAX_LENGTH))
    read_requested_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_attempt_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    last_read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    connected_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    disconnected_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class MailboxFolder(Base):
    """A folder of a mailbox and how far it has been read."""

    __tablename__ = "mailbox_folders"
    __table_args__ = (UniqueConstraint("mailbox_id", "kind"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    mailbox_id: Mapped[UUID] = mapped_column(ForeignKey("mailboxes.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(KIND_MAX_LENGTH))
    name: Mapped[str] = mapped_column(String(FOLDER_NAME_MAX_LENGTH))
    uidvalidity: Mapped[int | None] = mapped_column(BigInteger)
    last_uid: Mapped[int | None] = mapped_column(BigInteger)
