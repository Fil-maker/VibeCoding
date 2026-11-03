"""Response models of reply chains; `Address` also shapes the JSON columns of emails."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict


@dataclass(frozen=True)
class ChainDocument:
    """A chain as the placement engine and the rules read it, with its reading-order key."""

    chain_id: UUID
    subject: str  # of the first email
    first_sent_at: datetime
    first_key: str  # the key of the first email
    document: str
    senders: tuple[str, ...]  # distinct lower-cased `from` addresses of the chain's emails, sorted


@dataclass(frozen=True)
class ChainFacts:
    """What a tree shows of a chain; `participants` are the addresses but the user's own."""

    chain_id: UUID
    subject: str  # of the first email
    first_sent_at: datetime
    first_key: str
    latest_email_at: datetime
    email_count: int
    participants: tuple[str, ...]


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
