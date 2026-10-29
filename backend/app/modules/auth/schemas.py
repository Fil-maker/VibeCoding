"""Request and response models of sign-in and sessions."""

from uuid import UUID

from pydantic import BaseModel

from app.platform.validation import (
    EmailAddress,
    LinkToken,
    NewPassword,
    RequestModel,
    SignInEmail,
    SignInPassword,
)


class Me(BaseModel):
    """The signed-in user."""

    user_id: UUID
    name: str
    email: str


class SignInRequest(RequestModel):
    """The sign-in form."""

    email: SignInEmail
    password: SignInPassword


class EmailConfirmationRequest(RequestModel):
    """The token from the confirmation link."""

    token: LinkToken


class PasswordResetRequest(RequestModel):
    """The email to send a reset link to."""

    email: EmailAddress


class PasswordResetCompletion(RequestModel):
    """The token from the reset link and the new password."""

    token: LinkToken
    password: NewPassword
