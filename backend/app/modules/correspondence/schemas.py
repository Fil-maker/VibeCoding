"""Response models of reply chains; `Address` also shapes the JSON columns of emails."""

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


class Address(BaseModel):
    """An email address with the name written beside it, if any."""

    model_config = ConfigDict(frozen=True)

    address: str
    name: str | None = None


class ReplyChainSummary(BaseModel):
    """A row of the list of reply chains."""

    id: UUID
    subject: str
    participants: list[Address]
    email_count: int
    latest_email_at: datetime


class EmailView(BaseModel):
    """One email of a reply chain."""

    id: UUID
    sender: Address
    to: list[Address]
    cc: list[Address]
    sent_at: datetime
    subject: str
    text: str
    attachment_names: list[str]


class ReplyChain(BaseModel):
    """A reply chain with its emails, the oldest first."""

    id: UUID
    subject: str
    participants: list[Address]
    emails: list[EmailView]
