"""The shared page of a list answer and keyset cursors; a cursor is opaque to the client."""

import base64
import binascii
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

PAGE_DEFAULT_LIMIT = 50
PAGE_MAX_LIMIT = 100
CURSOR_MAX_LENGTH = 200


class InvalidCursor(Exception):
    """The cursor is not one this app issued; answered as 400 `invalid_cursor`."""


class Page[T](BaseModel):
    """One page of a list; `next_cursor` is `None` on the last page."""

    items: list[T]
    next_cursor: str | None


@dataclass(frozen=True)
class Cursor:
    """The sort position of the last item of a page: a timestamp and the id that breaks ties."""

    moment: datetime
    id: UUID


def encode_cursor(cursor: Cursor) -> str:
    """The opaque text of a cursor."""
    raw = f"{cursor.moment.isoformat()}|{cursor.id}"
    return base64.urlsafe_b64encode(raw.encode("ascii")).decode("ascii")


def decode_cursor(text: str) -> Cursor:
    """The cursor behind a text; `InvalidCursor` for anything else."""
    try:
        raw = base64.urlsafe_b64decode(text.encode("ascii")).decode("ascii")
        moment_text, id_text = raw.split("|")
        moment = datetime.fromisoformat(moment_text)
        if moment.tzinfo is None:
            raise ValueError("the moment has no timezone")
        return Cursor(moment=moment, id=UUID(id_text))
    except (ValueError, binascii.Error) as e:
        raise InvalidCursor("the cursor is broken") from e
