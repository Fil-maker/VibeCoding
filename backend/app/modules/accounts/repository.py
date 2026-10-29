"""Named queries over users."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts.models import User


@dataclass(frozen=True)
class UserRecord:
    """A user; the shape other modules see."""

    id: UUID
    name: str
    email: str
    password_hash: str
    confirmed_at: datetime | None


def _record(user: User) -> UserRecord:
    return UserRecord(
        id=user.id,
        name=user.name,
        email=user.email,
        password_hash=user.password_hash,
        confirmed_at=user.confirmed_at,
    )


async def find_by_email(session: AsyncSession, email: str) -> UserRecord | None:
    """The user with this normalized email.

    Installation-wide on purpose: an email belongs to at most one user (FR-1), and sign-in,
    registration and password reset start without a signed-in user.
    """
    user = (await session.execute(select(User).where(User.email == email))).scalar_one_or_none()
    return _record(user) if user is not None else None


async def find_by_id(session: AsyncSession, user_id: UUID) -> UserRecord | None:
    """The user with this id, or `None`."""
    user = (await session.execute(select(User).where(User.id == user_id))).scalar_one_or_none()
    return _record(user) if user is not None else None


async def add_user(
    session: AsyncSession, *, name: str, email: str, password_hash: str, now: datetime
) -> UserRecord:
    """Insert an unconfirmed user."""
    user = User(
        email=email, name=name, password_hash=password_hash, confirmed_at=None, created_at=now
    )
    session.add(user)
    await session.flush()
    return _record(user)


async def delete_user(session: AsyncSession, user_id: UUID) -> None:
    """Delete a user; the database cascades to their sessions and tokens."""
    await session.execute(delete(User).where(User.id == user_id))


async def mark_confirmed(session: AsyncSession, user_id: UUID, now: datetime) -> None:
    """Set the confirmation time of a user."""
    await session.execute(update(User).where(User.id == user_id).values(confirmed_at=now))


async def set_password_hash(session: AsyncSession, user_id: UUID, password_hash: str) -> None:
    """Replace the stored password hash of a user."""
    await session.execute(
        update(User).where(User.id == user_id).values(password_hash=password_hash)
    )
