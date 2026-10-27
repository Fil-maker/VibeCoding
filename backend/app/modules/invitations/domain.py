"""Pure logic of invitations: when one is open, its status and the page cursor."""

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from typing import Literal
from uuid import UUID

from app.modules.invitations.errors import InvalidCursor

InvitationStatus = Literal["sent", "not_sent", "accepted", "revoked", "expired"]
CURSOR_SEPARATOR = "|"


class Delivery(StrEnum):
    """Where the invitation email stands; the invitation row is the outbox."""

    PENDING = "pending"
    SENT = "sent"
    FAILED = "failed"


@dataclass(frozen=True)
class InvitationRecord:
    """An invitation as the service sees it."""

    id: UUID
    organization_id: UUID
    email: str
    delivery: Delivery
    sent_at: datetime | None
    expires_at: datetime
    accepted_at: datetime | None
    revoked_at: datetime | None
    created_at: datetime


def is_open(record: InvitationRecord, now: datetime) -> bool:
    """An invitation is open until it is accepted, revoked or expired."""
    return record.accepted_at is None and record.revoked_at is None and record.expires_at > now


def status_of(record: InvitationRecord, now: datetime) -> InvitationStatus:
    """The one status shown to the administrator."""
    if record.accepted_at is not None:
        return "accepted"
    if record.revoked_at is not None:
        return "revoked"
    if record.expires_at <= now:
        return "expired"
    return "sent" if record.delivery is Delivery.SENT else "not_sent"


def encode_cursor(record: InvitationRecord) -> str:
    """The cursor that continues the list after this invitation."""
    raw = f"{record.created_at.isoformat()}{CURSOR_SEPARATOR}{record.id}"
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> tuple[datetime, UUID]:
    """The position a cursor stands for; anything not issued by `encode_cursor` is refused."""
    try:
        raw = base64.urlsafe_b64decode(cursor.encode("ascii")).decode("utf-8")
        created_at, _, identifier = raw.partition(CURSOR_SEPARATOR)
        return datetime.fromisoformat(created_at), UUID(identifier)
    except (ValueError, binascii.Error) as e:
        raise InvalidCursor from e
