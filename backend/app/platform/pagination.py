"""The shared page of a list answer; the cursor is opaque to the client."""

from pydantic import BaseModel

PAGE_DEFAULT_LIMIT = 50
PAGE_MAX_LIMIT = 100
CURSOR_MAX_LENGTH = 200


class Page[T](BaseModel):
    """One page of a list; `next_cursor` is `None` on the last page."""

    items: list[T]
    next_cursor: str | None
