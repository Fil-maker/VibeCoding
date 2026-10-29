"""The authenticated caller of a request: who they are."""

from dataclasses import dataclass
from uuid import UUID


@dataclass(frozen=True)
class AuthContext:
    """Every owner-scoped query takes its `user_id` from here, never from the request."""

    user_id: UUID
