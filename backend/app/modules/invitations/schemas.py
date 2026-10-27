"""Request and response models of invitations."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from app.modules.invitations.domain import InvitationStatus
from app.platform.validation import EmailAddress, LinkToken, NewPassword, PersonName, RequestModel


class Invitation(BaseModel):
    """An invitation in the administrator's list."""

    id: UUID
    email: str
    sent_at: datetime | None
    expires_at: datetime
    status: InvitationStatus


class InvitationRequest(RequestModel):
    """The email to invite."""

    email: EmailAddress


class InvitationToken(RequestModel):
    """The token from the invitation link."""

    token: LinkToken


class InvitationPreview(BaseModel):
    """What the invitation page shows before the person joins."""

    organization_name: str
    email: str


class InvitationAcceptance(RequestModel):
    """The token from the link and the new member's name and password."""

    token: LinkToken
    name: PersonName
    password: NewPassword
