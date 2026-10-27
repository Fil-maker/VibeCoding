"""Pure logic of members: the page cursor."""

import base64
import binascii
import json
from uuid import UUID

from app.modules.accounts.errors import InvalidCursor
from app.modules.accounts.repository import MemberRecord


def encode_cursor(record: MemberRecord) -> str:
    """The cursor that continues the members list after this member."""
    raw = json.dumps([record.name, str(record.id)])
    return base64.urlsafe_b64encode(raw.encode("utf-8")).decode("ascii")


def decode_cursor(cursor: str) -> tuple[str, UUID]:
    """The position a cursor stands for; anything not issued by `encode_cursor` is refused."""
    try:
        name, identifier = json.loads(base64.urlsafe_b64decode(cursor.encode("ascii")))
        if not isinstance(name, str) or not isinstance(identifier, str):
            raise InvalidCursor
        return name, UUID(identifier)
    except (ValueError, TypeError, binascii.Error) as e:
        raise InvalidCursor from e
