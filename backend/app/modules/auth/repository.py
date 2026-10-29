"""Named queries over sessions, emailed tokens and sign-in failures."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, insert, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.auth.models import SignInFailure, UserSession, UserToken

CONFIRM_EMAIL = "confirm_email"
RESET_PASSWORD = "reset_password"


async def add_session(
    session: AsyncSession,
    *,
    user_id: UUID,
    token_hash: str,
    now: datetime,
    expires_at: datetime,
) -> None:
    """Store a new session by its token hash."""
    session.add(
        UserSession(
            user_id=user_id,
            token_hash=token_hash,
            created_at=now,
            expires_at=expires_at,
        )
    )
    await session.flush()


async def find_live_session(session: AsyncSession, token_hash: str, now: datetime) -> UUID | None:
    """The user id of a session that has not expired."""
    statement = select(UserSession.user_id).where(
        UserSession.token_hash == token_hash, UserSession.expires_at > now
    )
    return (await session.execute(statement)).scalar_one_or_none()


async def delete_session(session: AsyncSession, token_hash: str) -> None:
    """End one session."""
    await session.execute(delete(UserSession).where(UserSession.token_hash == token_hash))


async def delete_sessions_of_user(session: AsyncSession, user_id: UUID) -> None:
    """End every session of a user."""
    await session.execute(delete(UserSession).where(UserSession.user_id == user_id))


async def replace_user_token(
    session: AsyncSession,
    *,
    user_id: UUID,
    purpose: str,
    token_hash: str,
    now: datetime,
    expires_at: datetime,
) -> None:
    """Store a token and delete the user's earlier ones of the same purpose."""
    await delete_user_tokens(session, user_id, purpose)
    session.add(
        UserToken(
            user_id=user_id,
            purpose=purpose,
            token_hash=token_hash,
            created_at=now,
            expires_at=expires_at,
        )
    )
    await session.flush()


async def consume_user_token(
    session: AsyncSession, token_hash: str, purpose: str, now: datetime
) -> UUID | None:
    """Delete and return a live token in one statement, so a link works once."""
    statement = (
        delete(UserToken)
        .where(
            UserToken.token_hash == token_hash,
            UserToken.purpose == purpose,
            UserToken.expires_at > now,
        )
        .returning(UserToken.user_id)
    )
    return (await session.execute(statement)).scalar_one_or_none()


async def delete_user_tokens(session: AsyncSession, user_id: UUID, purpose: str) -> None:
    """Delete a user's tokens of one purpose."""
    await session.execute(
        delete(UserToken).where(
            UserToken.user_id == user_id,
            UserToken.purpose == purpose,
        )
    )


async def add_failure(session: AsyncSession, email: str, now: datetime) -> None:
    """Record a failed sign-in."""
    await session.execute(insert(SignInFailure).values(email=email, occurred_at=now))


async def list_failures(session: AsyncSession, email: str) -> list[datetime]:
    """The recorded failure times of an email."""
    statement = select(SignInFailure.occurred_at).where(SignInFailure.email == email)
    return list((await session.execute(statement)).scalars())


async def delete_failures(session: AsyncSession, email: str) -> None:
    """Clear an email's failures."""
    await session.execute(delete(SignInFailure).where(SignInFailure.email == email))


async def delete_failures_before(session: AsyncSession, email: str, before: datetime) -> None:
    """Drop an email's failures older than `before`."""
    await session.execute(
        delete(SignInFailure).where(
            SignInFailure.email == email, SignInFailure.occurred_at < before
        )
    )
