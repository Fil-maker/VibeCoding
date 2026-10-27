"""Named queries over organizations and users."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import delete, func, select, tuple_, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts.models import Organization, User
from app.platform.auth_context import Role


@dataclass(frozen=True)
class UserRecord:
    """A user with the name of their organization; the shape other modules see."""

    id: UUID
    organization_id: UUID
    organization_name: str
    name: str
    email: str
    role: Role
    password_hash: str
    is_active: bool
    confirmed_at: datetime | None


def _record(user: User, organization: Organization) -> UserRecord:
    return UserRecord(
        id=user.id,
        organization_id=user.organization_id,
        organization_name=organization.name,
        name=user.name,
        email=user.email,
        role=Role(user.role),
        password_hash=user.password_hash,
        is_active=user.is_active,
        confirmed_at=user.confirmed_at,
    )


async def find_by_email(session: AsyncSession, email: str) -> UserRecord | None:
    """The user with this normalized email, whatever the organization.

    Installation-wide on purpose: an email belongs to at most one user of the installation (FR-1),
    and sign-in, registration and password reset start without an organization.
    """
    statement = (
        select(User, Organization)
        .join(Organization, Organization.id == User.organization_id)
        .where(User.email == email)
    )
    row = (await session.execute(statement)).one_or_none()
    return _record(row[0], row[1]) if row is not None else None


async def find_by_id(
    session: AsyncSession, organization_id: UUID, user_id: UUID
) -> UserRecord | None:
    """The user with this id in the organization, or `None`."""
    statement = (
        select(User, Organization)
        .join(Organization, Organization.id == User.organization_id)
        .where(User.organization_id == organization_id, User.id == user_id)
    )
    row = (await session.execute(statement)).one_or_none()
    return _record(row[0], row[1]) if row is not None else None


async def add_organization_with_administrator(
    session: AsyncSession,
    *,
    organization_name: str,
    name: str,
    email: str,
    password_hash: str,
    now: datetime,
) -> UserRecord:
    """Insert an organization and its first, unconfirmed administrator."""
    organization = Organization(name=organization_name, created_at=now)
    session.add(organization)
    await session.flush()
    user = User(
        organization_id=organization.id,
        email=email,
        name=name,
        password_hash=password_hash,
        role=Role.ADMINISTRATOR.value,
        is_active=True,
        confirmed_at=None,
        created_at=now,
    )
    session.add(user)
    await session.flush()
    return _record(user, organization)


async def get_organization_name(
    session: AsyncSession, organization_id: UUID, *, lock: bool = False
) -> str | None:
    """The name of an organization; `lock` holds its row until the transaction ends."""
    statement = select(Organization.name).where(Organization.id == organization_id)
    if lock:
        statement = statement.with_for_update()
    return (await session.execute(statement)).scalar_one_or_none()


async def add_confirmed_employee(
    session: AsyncSession,
    *,
    organization_id: UUID,
    name: str,
    email: str,
    password_hash: str,
    now: datetime,
) -> UUID:
    """Insert an active, already confirmed employee; return their id."""
    user = User(
        organization_id=organization_id,
        email=email,
        name=name,
        password_hash=password_hash,
        role=Role.EMPLOYEE.value,
        is_active=True,
        confirmed_at=now,
        created_at=now,
    )
    session.add(user)
    await session.flush()
    return user.id


async def delete_organization(session: AsyncSession, organization_id: UUID) -> None:
    """Delete an organization; the database cascades to its users, sessions and tokens."""
    await session.execute(delete(Organization).where(Organization.id == organization_id))


async def mark_confirmed(
    session: AsyncSession, organization_id: UUID, user_id: UUID, now: datetime
) -> None:
    """Set the confirmation time of a user of the organization."""
    await session.execute(
        update(User)
        .where(User.organization_id == organization_id, User.id == user_id)
        .values(confirmed_at=now)
    )


async def set_password_hash(
    session: AsyncSession, organization_id: UUID, user_id: UUID, password_hash: str
) -> None:
    """Replace the stored password hash of a user of the organization."""
    await session.execute(
        update(User)
        .where(User.organization_id == organization_id, User.id == user_id)
        .values(password_hash=password_hash)
    )


@dataclass(frozen=True)
class MemberRecord:
    """A confirmed member as the members list and the member actions see them."""

    id: UUID
    name: str
    email: str
    role: Role
    is_active: bool


def _member(user: User) -> MemberRecord:
    return MemberRecord(
        id=user.id,
        name=user.name,
        email=user.email,
        role=Role(user.role),
        is_active=user.is_active,
    )


async def list_members(
    session: AsyncSession,
    organization_id: UUID,
    *,
    limit: int,
    after: tuple[str, UUID] | None,
) -> list[MemberRecord]:
    """At most `limit` confirmed members of the organization by name, after the cursor position."""
    statement = select(User).where(
        User.organization_id == organization_id, User.confirmed_at.is_not(None)
    )
    if after is not None:
        statement = statement.where(tuple_(User.name, User.id) > tuple_(*after))
    statement = statement.order_by(User.name, User.id).limit(limit)
    return [_member(user) for user in (await session.execute(statement)).scalars()]


async def find_member(
    session: AsyncSession, organization_id: UUID, member_id: UUID
) -> MemberRecord | None:
    """The confirmed member with this id in the organization, or `None`."""
    statement = select(User).where(
        User.organization_id == organization_id,
        User.id == member_id,
        User.confirmed_at.is_not(None),
    )
    user = (await session.execute(statement)).scalar_one_or_none()
    return _member(user) if user is not None else None


async def count_active_administrators(session: AsyncSession, organization_id: UUID) -> int:
    """How many confirmed, active administrators the organization has."""
    statement = (
        select(func.count())
        .select_from(User)
        .where(
            User.organization_id == organization_id,
            User.role == Role.ADMINISTRATOR.value,
            User.is_active.is_(True),
            User.confirmed_at.is_not(None),
        )
    )
    return (await session.execute(statement)).scalar_one()


async def set_member_active(
    session: AsyncSession, organization_id: UUID, member_id: UUID, *, is_active: bool
) -> None:
    """Switch the active flag of a member of the organization."""
    await session.execute(
        update(User)
        .where(User.organization_id == organization_id, User.id == member_id)
        .values(is_active=is_active)
    )


async def set_member_role(
    session: AsyncSession, organization_id: UUID, member_id: UUID, role: Role
) -> None:
    """Replace the role of a member of the organization."""
    await session.execute(
        update(User)
        .where(User.organization_id == organization_id, User.id == member_id)
        .values(role=role.value)
    )
