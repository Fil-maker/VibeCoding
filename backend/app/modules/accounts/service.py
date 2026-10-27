"""Use cases of accounts: registering an organization and managing its members."""

from dataclasses import replace
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts import repository
from app.modules.accounts.domain import decode_cursor, encode_cursor
from app.modules.accounts.emails import confirmation_email
from app.modules.accounts.errors import (
    CannotDeactivateSelf,
    EmailTaken,
    LastAdministrator,
    MemberInactive,
    MemberNotFound,
)
from app.modules.accounts.repository import UserRecord
from app.modules.accounts.schemas import Member, RegistrationRequest, RegistrationResult
from app.modules.auth.service import end_sessions_of_user, issue_confirmation_token
from app.platform.auth_context import AuthContext, Role
from app.platform.clock import Clock
from app.platform.db import get_database_session
from app.platform.logging import get_logger
from app.platform.mail import MailDeliveryError, MailSender
from app.platform.pagination import Page
from app.platform.passwords import hash_password
from app.platform.settings import Settings

LOG = get_logger(__name__)


async def register_organization(
    session: AsyncSession,
    settings: Settings,
    clock: Clock,
    mail: MailSender,
    request: RegistrationRequest,
) -> RegistrationResult:
    """Create the organization and its unconfirmed administrator, then email the link.

    An unconfirmed registration of the same email is replaced (FR-3). The email goes out after
    the commit; a mail failure is reported, not raised.
    """
    now = clock.now()
    password_hash = await hash_password(request.password)
    try:
        async with session.begin():
            existing = await repository.find_by_email(session, request.email)
            if existing is not None:
                if existing.confirmed_at is not None:
                    raise EmailTaken
                await repository.delete_organization(session, existing.organization_id)
            user = await repository.add_organization_with_administrator(
                session,
                organization_name=request.organization_name,
                name=request.name,
                email=request.email,
                password_hash=password_hash,
                now=now,
            )
            token = await issue_confirmation_token(
                session, settings, user.id, user.organization_id, now
            )
    except IntegrityError as e:
        if isinstance(e.orig, UniqueViolation):
            raise EmailTaken from e
        raise
    message = confirmation_email(
        to=user.email,
        name=user.name,
        app_base_url=settings.app_base_url,
        token=token,
        hours=settings.confirmation_link_hours,
    )
    try:
        await mail.send(message)
    except MailDeliveryError:
        LOG.warning("confirmation email was not sent for user %s", user.id)
        return RegistrationResult(email=user.email, email_sent=False)
    return RegistrationResult(email=user.email, email_sent=True)


async def join_organization_as_employee(
    session: AsyncSession,
    *,
    organization_id: UUID,
    name: str,
    email: str,
    password_hash: str,
    now: datetime,
) -> UserRecord:
    """Add a confirmed, active employee inside the caller's transaction.

    A confirmed user of the email makes it taken. An unconfirmed registration of the email is
    replaced, as a repeated registration does (FR-3).
    """
    existing = await repository.find_by_email(session, email)
    if existing is not None:
        if existing.confirmed_at is not None:
            raise EmailTaken
        await repository.delete_organization(session, existing.organization_id)
    user_id = await repository.add_confirmed_employee(
        session,
        organization_id=organization_id,
        name=name,
        email=email,
        password_hash=password_hash,
        now=now,
    )
    record = await repository.find_by_id(session, organization_id, user_id)
    if record is None:
        raise RuntimeError("the employee row vanished inside its own transaction")
    return record


def _view(record: repository.MemberRecord) -> Member:
    return Member(
        id=record.id,
        name=record.name,
        email=record.email,
        role=record.role.value,
        is_active=record.is_active,
    )


async def _lock_and_find(
    session: AsyncSession, context: AuthContext, member_id: UUID
) -> repository.MemberRecord:
    """Lock the organization row (FR-16), then find the member inside it or raise."""
    await repository.get_organization_name(session, context.organization_id, lock=True)
    record = await repository.find_member(session, context.organization_id, member_id)
    if record is None:
        raise MemberNotFound
    return record


async def _keeps_another_administrator(session: AsyncSession, context: AuthContext) -> bool:
    return await repository.count_active_administrators(session, context.organization_id) > 1


async def list_members(
    session: AsyncSession, context: AuthContext, *, limit: int, cursor: str | None
) -> Page[Member]:
    """A page of the organization's confirmed members, ordered by name."""
    after = decode_cursor(cursor) if cursor is not None else None
    async with session.begin():
        records = await repository.list_members(
            session, context.organization_id, limit=limit + 1, after=after
        )
    page = records[:limit]
    return Page[Member](
        items=[_view(record) for record in page],
        next_cursor=encode_cursor(page[-1]) if len(records) > limit else None,
    )


async def deactivate_member(session: AsyncSession, context: AuthContext, member_id: UUID) -> Member:
    """Deactivate a member and end their sessions; the last active administrator stays."""
    async with session.begin():
        record = await _lock_and_find(session, context, member_id)
        if record.id == context.user_id:
            raise CannotDeactivateSelf
        if (
            record.is_active
            and record.role is Role.ADMINISTRATOR
            and not await _keeps_another_administrator(session, context)
        ):
            raise LastAdministrator
        await repository.set_member_active(
            session, context.organization_id, record.id, is_active=False
        )
        await end_sessions_of_user(session, context.organization_id, record.id)
    return _view(replace(record, is_active=False))


async def reactivate_member(session: AsyncSession, context: AuthContext, member_id: UUID) -> Member:
    """Let a deactivated member sign in again."""
    async with session.begin():
        record = await _lock_and_find(session, context, member_id)
        await repository.set_member_active(
            session, context.organization_id, record.id, is_active=True
        )
    return _view(replace(record, is_active=True))


async def change_role(
    session: AsyncSession, context: AuthContext, member_id: UUID, role: Role
) -> Member:
    """Appoint an active employee an administrator, or make an administrator an employee."""
    async with session.begin():
        record = await _lock_and_find(session, context, member_id)
        if role is Role.ADMINISTRATOR and not record.is_active:
            raise MemberInactive
        if (
            role is Role.EMPLOYEE
            and record.is_active
            and record.role is Role.ADMINISTRATOR
            and not await _keeps_another_administrator(session, context)
        ):
            raise LastAdministrator
        await repository.set_member_role(session, context.organization_id, record.id, role)
    return _view(replace(record, role=role))


class AccountsService:
    """The use cases of accounts bound to one database session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register_organization(
        self, settings: Settings, clock: Clock, mail: MailSender, request: RegistrationRequest
    ) -> RegistrationResult:
        """See `register_organization`."""
        return await register_organization(self._session, settings, clock, mail, request)

    async def list_members(
        self, context: AuthContext, *, limit: int, cursor: str | None
    ) -> Page[Member]:
        """See `list_members`."""
        return await list_members(self._session, context, limit=limit, cursor=cursor)

    async def deactivate_member(self, context: AuthContext, member_id: UUID) -> Member:
        """See `deactivate_member`."""
        return await deactivate_member(self._session, context, member_id)

    async def reactivate_member(self, context: AuthContext, member_id: UUID) -> Member:
        """See `reactivate_member`."""
        return await reactivate_member(self._session, context, member_id)

    async def change_role(self, context: AuthContext, member_id: UUID, role: Role) -> Member:
        """See `change_role`."""
        return await change_role(self._session, context, member_id, role)


def get_accounts_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AccountsService:
    """Dependency factory of the accounts use cases."""
    return AccountsService(session)
