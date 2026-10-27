"""The authenticated caller of a request: who they are and which organization they belong to."""

from dataclasses import dataclass
from enum import StrEnum
from uuid import UUID


class Role(StrEnum):
    """The role of a user inside the organization."""

    ADMINISTRATOR = "administrator"
    EMPLOYEE = "employee"


@dataclass(frozen=True)
class AuthContext:
    """Every query takes its organization and owner scope from here, never from the request."""

    user_id: UUID
    organization_id: UUID
    role: Role
