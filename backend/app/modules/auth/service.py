"""Use cases of auth: sessions, sign-in with its lock, confirmation links and password reset."""

from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts import repository as accounts
from app.modules.accounts.repository import UserRecord
from app.modules.auth import repository
from app.modules.auth.domain import is_locked
from app.modules.auth.emails import password_reset_email
from app.modules.auth.errors import (
    AccountDisabled,
    EmailNotConfirmed,
    InvalidCredentials,
    InvalidLink,
    NotSignedIn,
    SignInLocked,
    SignInRefused,
)
from app.modules.auth.repository import TokenOwner
from app.modules.auth.schemas import Me, OrganizationRef, SignInRequest
from app.platform.auth_context import AuthContext
from app.platform.clock import Clock
from app.platform.db import get_database_session
from app.platform.logging import get_logger
from app.platform.mail import MailDeliveryError, MailSender
from app.platform.passwords import hash_password, verify_password
from app.platform.settings import Settings
from app.platform.tokens import hash_token, new_token

LOG = get_logger(__name__)


@dataclass(frozen=True)
class SignedIn:
    """A started session: the raw cookie token and the user it belongs to."""

    token: str
    me: Me


def me_of(record: UserRecord) -> Me:
    """The public view of a user."""
    return Me(
        user_id=record.id,
        name=record.name,
        email=record.email,
        role=record.role.value,
        organization=OrganizationRef(id=record.organization_id, name=record.organization_name),
    )


async def start_session(
    session: AsyncSession, settings: Settings, owner: TokenOwner, now: datetime
) -> str:
    """Store a new session inside the caller's transaction; return the raw cookie token."""
    token = new_token()
    await repository.add_session(
        session,
        owner=owner,
        token_hash=hash_token(token),
        now=now,
        expires_at=now + timedelta(days=settings.session_lifetime_days),
    )
    return token


async def issue_confirmation_token(
    session: AsyncSession, settings: Settings, user_id: UUID, organization_id: UUID, now: datetime
) -> str:
    """Store a confirmation token, replacing earlier ones, inside the caller's transaction."""
    token = new_token()
    await repository.replace_user_token(
        session,
        owner=TokenOwner(user_id=user_id, organization_id=organization_id),
        purpose=repository.CONFIRM_EMAIL,
        token_hash=hash_token(token),
        now=now,
        expires_at=now + timedelta(hours=settings.confirmation_link_hours),
    )
    return token


async def resolve_session(session: AsyncSession, token: str, now: datetime) -> AuthContext | None:
    """The caller behind a cookie token.

    `None` unless the session is live and the user is confirmed and active.
    """
    async with session.begin():
        owner = await repository.find_live_session(session, hash_token(token), now)
        if owner is None:
            return None
        record = await accounts.find_by_id(session, owner.organization_id, owner.user_id)
    if record is None or record.confirmed_at is None or not record.is_active:
        return None
    return AuthContext(user_id=record.id, organization_id=record.organization_id, role=record.role)


async def get_me(session: AsyncSession, context: AuthContext) -> Me:
    """The signed-in user's profile."""
    async with session.begin():
        record = await accounts.find_by_id(session, context.organization_id, context.user_id)
    if record is None:
        raise NotSignedIn
    return me_of(record)


async def sign_out(session: AsyncSession, token: str) -> None:
    """End the session of this cookie token only."""
    async with session.begin():
        await repository.delete_session(session, hash_token(token))


async def end_sessions_of_user(session: AsyncSession, organization_id: UUID, user_id: UUID) -> None:
    """End every session of a user of the organization; runs in the caller's transaction."""
    await repository.delete_sessions_of_user(session, organization_id, user_id)


async def _attempt_sign_in(
    session: AsyncSession, settings: Settings, request: SignInRequest, now: datetime
) -> SignedIn | SignInRefused:
    """Decide a sign-in inside the open transaction; a refusal is returned, not raised."""
    window = timedelta(minutes=settings.sign_in_failure_window_minutes)
    lock = timedelta(minutes=settings.sign_in_lock_minutes)
    # Failures stay as long as a lock they caused may last, not only for the counting window.
    await repository.delete_failures_before(session, request.email, now - window - lock)
    failures = await repository.list_failures(session, request.email)
    if is_locked(
        failures, now, max_failures=settings.sign_in_max_failures, window=window, lock=lock
    ):
        return SignInLocked()
    record = await accounts.find_by_email(session, request.email)
    check = await verify_password(record.password_hash if record else None, request.password)
    if record is None or not check.ok:
        await repository.add_failure(session, request.email, now)
        return InvalidCredentials()
    if record.confirmed_at is None:
        return EmailNotConfirmed()
    if not record.is_active:
        return AccountDisabled()
    await repository.delete_failures(session, request.email)
    if check.needs_rehash:
        await accounts.set_password_hash(
            session, record.organization_id, record.id, await hash_password(request.password)
        )
    owner = TokenOwner(user_id=record.id, organization_id=record.organization_id)
    return SignedIn(token=await start_session(session, settings, owner, now), me=me_of(record))


async def sign_in(
    session: AsyncSession, settings: Settings, clock: Clock, request: SignInRequest
) -> SignedIn:
    """Sign in with email and password; failures are recorded even though the call raises."""
    now = clock.now()
    async with session.begin():
        outcome = await _attempt_sign_in(session, settings, request, now)
    if isinstance(outcome, SignInRefused):
        raise outcome
    return outcome


async def confirm_email(
    session: AsyncSession, settings: Settings, clock: Clock, token: str
) -> SignedIn:
    """Confirm the registrant's email by a single-use link and sign them in."""
    now = clock.now()
    async with session.begin():
        owner = await repository.consume_user_token(
            session, hash_token(token), repository.CONFIRM_EMAIL, now
        )
        if owner is None:
            raise InvalidLink
        await accounts.mark_confirmed(session, owner.organization_id, owner.user_id, now)
        record = await accounts.find_by_id(session, owner.organization_id, owner.user_id)
        if record is None:
            raise InvalidLink
        session_token = await start_session(session, settings, owner, now)
    return SignedIn(token=session_token, me=me_of(record))


async def request_password_reset(
    session: AsyncSession, settings: Settings, clock: Clock, mail: MailSender, email: str
) -> None:
    """Email a reset link to a confirmed user; the caller learns nothing about the email."""
    now = clock.now()
    token = new_token()
    async with session.begin():
        record = await accounts.find_by_email(session, email)
        if record is None or record.confirmed_at is None:
            return
        await repository.replace_user_token(
            session,
            owner=TokenOwner(user_id=record.id, organization_id=record.organization_id),
            purpose=repository.RESET_PASSWORD,
            token_hash=hash_token(token),
            now=now,
            expires_at=now + timedelta(minutes=settings.password_reset_link_minutes),
        )
    message = password_reset_email(
        to=record.email,
        name=record.name,
        app_base_url=settings.app_base_url,
        token=token,
        minutes=settings.password_reset_link_minutes,
    )
    try:
        await mail.send(message)
    except MailDeliveryError:
        LOG.warning("password reset email was not sent for user %s", record.id)


async def complete_password_reset(
    session: AsyncSession, clock: Clock, token: str, password: str
) -> None:
    """Set a new password by a single-use link; ends all sessions and clears the sign-in lock."""
    now = clock.now()
    password_hash = await hash_password(password)
    async with session.begin():
        owner = await repository.consume_user_token(
            session, hash_token(token), repository.RESET_PASSWORD, now
        )
        record = (
            await accounts.find_by_id(session, owner.organization_id, owner.user_id)
            if owner
            else None
        )
        if owner is None or record is None:
            raise InvalidLink
        await accounts.set_password_hash(session, record.organization_id, record.id, password_hash)
        await repository.delete_sessions_of_user(session, record.organization_id, record.id)
        await repository.delete_failures(session, record.email)


class AuthService:
    """The use cases of auth bound to one database session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def confirm_email(self, settings: Settings, clock: Clock, token: str) -> SignedIn:
        """See `confirm_email`."""
        return await confirm_email(self._session, settings, clock, token)

    async def sign_in(self, settings: Settings, clock: Clock, request: SignInRequest) -> SignedIn:
        """See `sign_in`."""
        return await sign_in(self._session, settings, clock, request)

    async def sign_out(self, token: str) -> None:
        """See `sign_out`."""
        await sign_out(self._session, token)

    async def get_me(self, context: AuthContext) -> Me:
        """See `get_me`."""
        return await get_me(self._session, context)

    async def request_password_reset(
        self, settings: Settings, clock: Clock, mail: MailSender, email: str
    ) -> None:
        """See `request_password_reset`."""
        await request_password_reset(self._session, settings, clock, mail, email)

    async def complete_password_reset(self, clock: Clock, token: str, password: str) -> None:
        """See `complete_password_reset`."""
        await complete_password_reset(self._session, clock, token, password)


def get_auth_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AuthService:
    """Dependency factory of the auth use cases."""
    return AuthService(session)
