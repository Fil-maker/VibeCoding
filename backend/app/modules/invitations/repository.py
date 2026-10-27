"""Named queries over invitations; every query of an administrator filters by organization."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.invitations.domain import Delivery, InvitationRecord
from app.modules.invitations.models import Invitation


def _record(row: Invitation) -> InvitationRecord:
    return InvitationRecord(
        id=row.id,
        organization_id=row.organization_id,
        email=row.email,
        delivery=Delivery(row.delivery),
        sent_at=row.sent_at,
        expires_at=row.expires_at,
        accepted_at=row.accepted_at,
        revoked_at=row.revoked_at,
        created_at=row.created_at,
    )


async def add_pending(
    session: AsyncSession,
    *,
    organization_id: UUID,
    email: str,
    invited_by_user_id: UUID,
    token_hash: str,
    now: datetime,
    expires_at: datetime,
) -> InvitationRecord:
    """Store a new invitation whose email is not yet sent."""
    row = Invitation(
        organization_id=organization_id,
        email=email,
        invited_by_user_id=invited_by_user_id,
        token_hash=token_hash,
        delivery=Delivery.PENDING.value,
        sent_at=None,
        expires_at=expires_at,
        accepted_at=None,
        accepted_user_id=None,
        revoked_at=None,
        created_at=now,
    )
    session.add(row)
    await session.flush()
    return _record(row)


async def has_open_for_email(
    session: AsyncSession, organization_id: UUID, email: str, now: datetime
) -> bool:
    """Whether the organization has an open invitation for this email."""
    statement = select(Invitation.id).where(
        Invitation.organization_id == organization_id,
        Invitation.email == email,
        Invitation.accepted_at.is_(None),
        Invitation.revoked_at.is_(None),
        Invitation.expires_at > now,
    )
    return (await session.execute(statement.limit(1))).first() is not None


async def get_in_organization(
    session: AsyncSession, organization_id: UUID, invitation_id: UUID, *, lock: bool = False
) -> InvitationRecord | None:
    """The invitation of this organization; `lock` holds its row until the transaction ends."""
    statement = select(Invitation).where(
        Invitation.organization_id == organization_id, Invitation.id == invitation_id
    )
    statement = statement.execution_options(populate_existing=True)
    if lock:
        statement = statement.with_for_update()
    row = (await session.execute(statement)).scalar_one_or_none()
    return _record(row) if row is not None else None


async def get_by_token_hash(
    session: AsyncSession, token_hash: str, *, lock: bool = False
) -> InvitationRecord | None:
    """The invitation behind a link token; the hash is the only key, so the scope is the link."""
    statement = select(Invitation).where(Invitation.token_hash == token_hash)
    statement = statement.execution_options(populate_existing=True)
    if lock:
        statement = statement.with_for_update()
    row = (await session.execute(statement)).scalar_one_or_none()
    return _record(row) if row is not None else None


async def list_newest_first(
    session: AsyncSession,
    organization_id: UUID,
    *,
    limit: int,
    after: tuple[datetime, UUID] | None,
) -> list[InvitationRecord]:
    """At most `limit` invitations of the organization, newest first, after the cursor position."""
    statement = select(Invitation).where(Invitation.organization_id == organization_id)
    if after is not None:
        statement = statement.where(tuple_(Invitation.created_at, Invitation.id) < tuple_(*after))
    statement = statement.order_by(Invitation.created_at.desc(), Invitation.id.desc()).limit(limit)
    return [_record(row) for row in (await session.execute(statement)).scalars()]


async def replace_link(
    session: AsyncSession,
    organization_id: UUID,
    invitation_id: UUID,
    *,
    token_hash: str,
    expires_at: datetime,
) -> None:
    """Give the invitation a new link; the earlier one stops working and nothing is sent yet."""
    await session.execute(
        update(Invitation)
        .where(Invitation.organization_id == organization_id, Invitation.id == invitation_id)
        .values(
            token_hash=token_hash,
            expires_at=expires_at,
            delivery=Delivery.PENDING.value,
            sent_at=None,
        )
    )


async def set_delivery(
    session: AsyncSession,
    organization_id: UUID,
    invitation_id: UUID,
    *,
    token_hash: str,
    delivery: Delivery,
    sent_at: datetime | None,
) -> None:
    """Record the send outcome, unless the link was replaced meanwhile."""
    await session.execute(
        update(Invitation)
        .where(
            Invitation.organization_id == organization_id,
            Invitation.id == invitation_id,
            Invitation.token_hash == token_hash,
        )
        .values(delivery=delivery.value, sent_at=sent_at)
    )


async def set_revoked(
    session: AsyncSession, organization_id: UUID, invitation_id: UUID, now: datetime
) -> None:
    """Mark the invitation of this organization revoked."""
    await session.execute(
        update(Invitation)
        .where(Invitation.organization_id == organization_id, Invitation.id == invitation_id)
        .values(revoked_at=now)
    )


async def set_accepted(
    session: AsyncSession, organization_id: UUID, invitation_id: UUID, user_id: UUID, now: datetime
) -> None:
    """Mark the invitation of this organization accepted by the user it created."""
    await session.execute(
        update(Invitation)
        .where(Invitation.organization_id == organization_id, Invitation.id == invitation_id)
        .values(accepted_at=now, accepted_user_id=user_id)
    )
