"""Tables of reply chains, the emails in them and the copies of an email in mailbox folders."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import BigInteger, DateTime, ForeignKey, Index, String, Text, UniqueConstraint
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base

KEY_MAX_LENGTH = 998
ADDRESS_MAX_LENGTH = 320


class ReplyChain(Base):
    """A reply chain of a user: emails joined by `In-Reply-To` and `References`."""

    __tablename__ = "reply_chains"
    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    latest_email_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


Index(
    "ix_reply_chains_user_id_latest_email_at_id",
    ReplyChain.user_id,
    ReplyChain.latest_email_at.desc(),
    ReplyChain.id,
)


class Email(Base):
    """An email stored once per user, whichever mailboxes and folders hold copies of it."""

    __tablename__ = "emails"
    __table_args__ = (
        UniqueConstraint("user_id", "key"),
        Index("ix_emails_chain_id_sent_at_id", "chain_id", "sent_at", "id"),
        Index("ix_emails_references", "references", postgresql_using="gin"),
        Index("ix_emails_user_id_in_reply_to", "user_id", "in_reply_to"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    chain_id: Mapped[UUID] = mapped_column(ForeignKey("reply_chains.id", ondelete="CASCADE"))
    key: Mapped[str] = mapped_column(String(KEY_MAX_LENGTH))
    message_id: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    in_reply_to: Mapped[str | None] = mapped_column(String(KEY_MAX_LENGTH))
    references: Mapped[list[str]] = mapped_column(ARRAY(Text))
    subject: Mapped[str] = mapped_column(Text)
    from_address: Mapped[str] = mapped_column(String(ADDRESS_MAX_LENGTH))
    from_name: Mapped[str | None] = mapped_column(Text)
    to_addresses: Mapped[list[dict[str, str | None]]] = mapped_column(JSONB)
    cc_addresses: Mapped[list[dict[str, str | None]]] = mapped_column(JSONB)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    text: Mapped[str] = mapped_column(Text)
    attachment_names: Mapped[list[str]] = mapped_column(ARRAY(Text))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class EmailCopy(Base):
    """One copy of an email in a folder of a mailbox, by the IMAP UID."""

    __tablename__ = "email_copies"
    __table_args__ = (UniqueConstraint("folder_id", "uid"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    email_id: Mapped[UUID] = mapped_column(ForeignKey("emails.id", ondelete="CASCADE"), index=True)
    mailbox_id: Mapped[UUID] = mapped_column(
        ForeignKey("mailboxes.id", ondelete="CASCADE"), index=True
    )
    folder_id: Mapped[UUID] = mapped_column(ForeignKey("mailbox_folders.id", ondelete="CASCADE"))
    uid: Mapped[int] = mapped_column(BigInteger)
