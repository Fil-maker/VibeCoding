"""Use cases of accounts: registering a user."""

from typing import Annotated

from fastapi import Depends
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts import repository
from app.modules.accounts.emails import confirmation_email
from app.modules.accounts.errors import EmailTaken
from app.modules.accounts.schemas import RegistrationRequest, RegistrationResult
from app.modules.auth.service import issue_confirmation_token
from app.platform.clock import Clock
from app.platform.db import get_database_session
from app.platform.logging import get_logger
from app.platform.mail import MailDeliveryError, MailSender
from app.platform.passwords import hash_password
from app.platform.settings import Settings

LOG = get_logger(__name__)


async def register(
    session: AsyncSession,
    settings: Settings,
    clock: Clock,
    mail: MailSender,
    request: RegistrationRequest,
) -> RegistrationResult:
    """Create an unconfirmed user, then email the confirmation link.

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
                await repository.delete_user(session, existing.id)
            user = await repository.add_user(
                session,
                name=request.name,
                email=request.email,
                password_hash=password_hash,
                now=now,
            )
            token = await issue_confirmation_token(session, settings, user.id, now)
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


class AccountsService:
    """The use cases of accounts bound to one database session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def register(
        self, settings: Settings, clock: Clock, mail: MailSender, request: RegistrationRequest
    ) -> RegistrationResult:
        """See `register`."""
        return await register(self._session, settings, clock, mail, request)


def get_accounts_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> AccountsService:
    """Dependency factory of the accounts use cases."""
    return AccountsService(session)
