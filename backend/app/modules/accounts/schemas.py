"""Request and response models of registration."""

from typing import Literal
from uuid import UUID

from pydantic import BaseModel

from app.platform.validation import (
    EmailAddress,
    NewPassword,
    OrganizationName,
    PersonName,
    RequestModel,
)


class RegistrationRequest(RequestModel):
    """The registration form."""

    organization_name: OrganizationName
    name: PersonName
    email: EmailAddress
    password: NewPassword


class RegistrationResult(BaseModel):
    """The address the confirmation went to, and whether the mail server took it."""

    email: str
    email_sent: bool


class Member(BaseModel):
    """A confirmed member of the organization."""

    id: UUID
    name: str
    email: str
    role: Literal["administrator", "employee"]
    is_active: bool


class RoleChange(RequestModel):
    """The new role of a member."""

    role: Literal["administrator", "employee"]
