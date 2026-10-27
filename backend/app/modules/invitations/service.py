"""Use cases of invitations: invite, list, resend, revoke, preview and accept."""

from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts import repository as accounts
from app.modules.accounts import service as accounts_service
from app.modules.accounts.errors import EmailTaken
from app.modules.auth.repository import TokenOwner
from app.modules.auth.service import SignedIn, me_of, start_session
from app.modules.invitations import repository
from app.modules.invitations.domain import (
    Delivery,
    InvitationRecord,
    decode_cursor,
    encode_cursor,
    is_open,
    status_of,
)
from app.modules.invitations.emails import invitation_email
from app.modules.invitations.errors import InvalidInvitation, InvitationExists, InvitationNotOpen
from app.modules.invitations.schemas import (
    Invitation,
    InvitationAcceptance,
    InvitationPreview,
)
from app.platform.auth_context import AuthContext
from app.platform.clock import Clock
from app.platform.db import get_database_session
from app.platform.errors import NotFound
from app.platform.logging import get_logger
from app.platform.mail import MailDeliveryError, MailSender
from app.platform.pagination import Page
from app.platform.passwords import hash_password
from app.platform.settings import Settings
from app.platform.tokens import hash_token, new_token

LOG = get_logger(__name__)


def _view(record: InvitationRecord, now: datetime) -> Invitation:
    return Invitation(
        id=record.id,
        email=record.email,
        sent_at=record.sent_at,
        expires_at=record.expires_at,
        status=status_of(record, now),
    )


def _expiry(settings: Settings, now: datetime) -> datetime:
    return now + timedelta(days=settings.invitation_lifetime_days)


async def _deliver(
    session: AsyncSession,
    settings: Settings,
    clock: Clock,
    mail: MailSender,
    record: InvitationRecord,
    *,
    organization_name: str,
    token: str,
) -> InvitationRecord:
    """Send the email outside any transaction, then record the outcome in a second one."""
    message = invitation_email(
        to=record.email,
        organization_name=organization_name,
        app_base_url=settings.app_base_url,
        token=token,
        days=settings.invitation_lifetime_days,
    )
    try:
        await mail.send(message)
        delivery, sent_at = Delivery.SENT, clock.now()
    except MailDeliveryError:
        LOG.warning("invitation email was not sent for invitation %s", record.id)
        delivery, sent_at = Delivery.FAILED, None
    async with session.begin():
        await repository.set_delivery(
            session,
            record.organization_id,
            record.id,
            token_hash=hash_token(token),
            delivery=delivery,
            sent_at=sent_at,
        )
        updated = await repository.get_in_organization(session, record.organization_id, record.id)
    if updated is None:
        raise NotFound
    return updated


async def invite(
    session: AsyncSession,
    settings: Settings,
    clock: Clock,
    mail: MailSender,
    context: AuthContext,
    email: str,
) -> Invitation:
    """Invite an email to the administrator's organization and email the link."""
    now = clock.now()
    token = new_token()
    async with session.begin():
        # The organization lock serializes invitations: "open" depends on the clock.
        organization_name = await accounts.get_organization_name(
            session, context.organization_id, lock=True
        )
        if organization_name is None:
            raise NotFound
        user = await accounts.find_by_email(session, email)
        if user is not None and user.confirmed_at is not None:
            raise EmailTaken
        if await repository.has_open_for_email(session, context.organization_id, email, now):
            raise InvitationExists
        record = await repository.add_pending(
            session,
            organization_id=context.organization_id,
            email=email,
            invited_by_user_id=context.user_id,
            token_hash=hash_token(token),
            now=now,
            expires_at=_expiry(settings, now),
        )
    delivered = await _deliver(
        session, settings, clock, mail, record, organization_name=organization_name, token=token
    )
    return _view(delivered, clock.now())


async def list_invitations(
    session: AsyncSession,
    clock: Clock,
    context: AuthContext,
    *,
    limit: int,
    cursor: str | None,
) -> Page[Invitation]:
    """A page of the organization's invitations, newest first."""
    after = decode_cursor(cursor) if cursor is not None else None
    now = clock.now()
    async with session.begin():
        records = await repository.list_newest_first(
            session, context.organization_id, limit=limit + 1, after=after
        )
    page = records[:limit]
    has_more = len(records) > limit
    return Page[Invitation](
        items=[_view(record, now) for record in page],
        next_cursor=encode_cursor(page[-1]) if has_more else None,
    )


async def resend(
    session: AsyncSession,
    settings: Settings,
    clock: Clock,
    mail: MailSender,
    context: AuthContext,
    invitation_id: UUID,
) -> Invitation:
    """Replace the link of an open invitation and send it again."""
    now = clock.now()
    token = new_token()
    async with session.begin():
        record = await repository.get_in_organization(
            session, context.organization_id, invitation_id, lock=True
        )
        organization_name = await accounts.get_organization_name(session, context.organization_id)
        if record is None or organization_name is None:
            raise NotFound
        if not is_open(record, now):
            raise InvitationNotOpen
        await repository.replace_link(
            session,
            record.organization_id,
            record.id,
            token_hash=hash_token(token),
            expires_at=_expiry(settings, now),
        )
    delivered = await _deliver(
        session, settings, clock, mail, record, organization_name=organization_name, token=token
    )
    return _view(delivered, clock.now())


async def revoke(
    session: AsyncSession, clock: Clock, context: AuthContext, invitation_id: UUID
) -> Invitation:
    """Revoke an open invitation; one that is not open stays as it is."""
    now = clock.now()
    async with session.begin():
        record = await repository.get_in_organization(
            session, context.organization_id, invitation_id, lock=True
        )
        if record is None:
            raise NotFound
        if is_open(record, now):
            await repository.set_revoked(session, record.organization_id, record.id, now)
            record = await repository.get_in_organization(
                session, context.organization_id, invitation_id
            )
            if record is None:
                raise NotFound
    return _view(record, now)


async def preview(session: AsyncSession, clock: Clock, token: str) -> InvitationPreview:
    """The organization and email of an open invitation link."""
    now = clock.now()
    async with session.begin():
        record = await repository.get_by_token_hash(session, hash_token(token))
        if record is None or not is_open(record, now):
            raise InvalidInvitation
        organization_name = await accounts.get_organization_name(session, record.organization_id)
    if organization_name is None:
        raise InvalidInvitation
    return InvitationPreview(organization_name=organization_name, email=record.email)


async def accept(
    session: AsyncSession, settings: Settings, clock: Clock, request: InvitationAcceptance
) -> SignedIn:
    """Join the organization by an open invitation link and sign in."""
    now = clock.now()
    password_hash = await hash_password(request.password)
    try:
        async with session.begin():
            # The row lock makes a second acceptance of the same link wait and then fail.
            record = await repository.get_by_token_hash(
                session, hash_token(request.token), lock=True
            )
            if record is None or not is_open(record, now):
                raise InvalidInvitation
            user = await accounts_service.join_organization_as_employee(
                session,
                organization_id=record.organization_id,
                name=request.name,
                email=record.email,
                password_hash=password_hash,
                now=now,
            )
            await repository.set_accepted(session, record.organization_id, record.id, user.id, now)
            owner = TokenOwner(user_id=user.id, organization_id=user.organization_id)
            session_token = await start_session(session, settings, owner, now)
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise EmailTaken from e
        raise
    return SignedIn(token=session_token, me=me_of(user))


class InvitationsService:
    """The use cases of invitations bound to one database session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def invite(
        self, settings: Settings, clock: Clock, mail: MailSender, context: AuthContext, email: str
    ) -> Invitation:
        """See `invite`."""
        return await invite(self._session, settings, clock, mail, context, email)

    async def list_invitations(
        self, clock: Clock, context: AuthContext, *, limit: int, cursor: str | None
    ) -> Page[Invitation]:
        """See `list_invitations`."""
        return await list_invitations(self._session, clock, context, limit=limit, cursor=cursor)

    async def resend(
        self,
        settings: Settings,
        clock: Clock,
        mail: MailSender,
        context: AuthContext,
        invitation_id: UUID,
    ) -> Invitation:
        """See `resend`."""
        return await resend(self._session, settings, clock, mail, context, invitation_id)

    async def revoke(self, clock: Clock, context: AuthContext, invitation_id: UUID) -> Invitation:
        """See `revoke`."""
        return await revoke(self._session, clock, context, invitation_id)

    async def preview(self, clock: Clock, token: str) -> InvitationPreview:
        """See `preview`."""
        return await preview(self._session, clock, token)

    async def accept(
        self, settings: Settings, clock: Clock, request: InvitationAcceptance
    ) -> SignedIn:
        """See `accept`."""
        return await accept(self._session, settings, clock, request)


def get_invitations_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> InvitationsService:
    """Dependency factory of the invitations use cases."""
    return InvitationsService(session)
