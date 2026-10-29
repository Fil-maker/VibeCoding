"""Request and response models of registration."""

from pydantic import BaseModel

from app.platform.validation import (
    EmailAddress,
    NewPassword,
    PersonName,
    RequestModel,
)


class RegistrationRequest(RequestModel):
    """The registration form."""

    name: PersonName
    email: EmailAddress
    password: NewPassword


class RegistrationResult(BaseModel):
    """The address the confirmation went to, and whether the mail server took it."""

    email: str
    email_sent: bool
