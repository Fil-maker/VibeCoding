"""Named queries over reply chains, emails and their copies.

Every query is owner-scoped unless its docstring says otherwise.
"""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy import and_, delete, func, or_, select, update
from sqlalchemy.dialects.postgresql import distinct_on, insert
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.correspondence.domain import ChainRef, ParsedEmail
from app.modules.correspondence.models import Email, EmailCopy, ReplyChain
from app.platform.pagination import Cursor


@dataclass(frozen=True)
class StoredEmail:
    """Where a stored email lives."""

    id: UUID
    chain_id: UUID


@dataclass(frozen=True)
class ChainRow:
    """A chain of the list."""

    id: UUID
    latest_email_at: datetime


@dataclass(frozen=True)
class AddressRow:
    """The address columns of one email, in the order of its chain."""

    chain_id: UUID
    from_address: str
    from_name: str | None
    to_addresses: list[dict[str, str | None]]
    cc_addresses: list[dict[str, str | None]]


async def get_email_by_key_for_owner(
    session: AsyncSession, user_id: UUID, key: str
) -> StoredEmail | None:
    """The user's email with this key."""
    row = (
        await session.execute(
            select(Email.id, Email.chain_id).where(Email.user_id == user_id, Email.key == key)
        )
    ).one_or_none()
    return StoredEmail(row.id, row.chain_id) if row is not None else None


async def list_chain_ids_of_keys_for_owner(
    session: AsyncSession, user_id: UUID, keys: Sequence[str]
) -> list[UUID]:
    """The chains of the user's stored emails with these keys."""
    if not keys:
        return []
    rows = await session.execute(
        select(Email.chain_id).where(Email.user_id == user_id, Email.key.in_(keys)).distinct()
    )
    return list(rows.scalars())


async def list_chain_ids_naming_key_for_owner(
    session: AsyncSession, user_id: UUID, key: str
) -> list[UUID]:
    """The chains of the user's stored emails whose `In-Reply-To` or `References` name the key."""
    rows = await session.execute(
        select(Email.chain_id)
        .where(
            Email.user_id == user_id,
            or_(Email.references.contains([key]), Email.in_reply_to == key),
        )
        .distinct()
    )
    return list(rows.scalars())


async def lock_chains_for_owner(
    session: AsyncSession, user_id: UUID, chain_ids: Sequence[UUID]
) -> list[ChainRef]:
    """Lock the user's chains in id order (so two merges cannot deadlock) and return them."""
    if not chain_ids:
        return []
    rows = await session.execute(
        select(ReplyChain.id, ReplyChain.created_at)
        .where(ReplyChain.user_id == user_id, ReplyChain.id.in_(chain_ids))
        .order_by(ReplyChain.id)
        .with_for_update()
    )
    return [ChainRef(row.id, row.created_at) for row in rows]


async def add_chain_for_owner(
    session: AsyncSession, user_id: UUID, *, latest_email_at: datetime, now: datetime
) -> UUID:
    """Create an empty chain."""
    chain = ReplyChain(user_id=user_id, latest_email_at=latest_email_at, created_at=now)
    session.add(chain)
    await session.flush()
    return chain.id


async def move_emails_to_chain_for_owner(
    session: AsyncSession, user_id: UUID, from_ids: Sequence[UUID], to_id: UUID
) -> None:
    """Move the emails of some chains to another one and delete the emptied chains."""
    await session.execute(
        update(Email)
        .where(Email.user_id == user_id, Email.chain_id.in_(from_ids))
        .values(chain_id=to_id)
    )
    await session.execute(
        delete(ReplyChain).where(ReplyChain.user_id == user_id, ReplyChain.id.in_(from_ids))
    )


async def delete_chain_for_owner(session: AsyncSession, user_id: UUID, chain_id: UUID) -> None:
    """Delete a chain (its emails go with it)."""
    await session.execute(
        delete(ReplyChain).where(ReplyChain.user_id == user_id, ReplyChain.id == chain_id)
    )


async def refresh_chain_latest_email_at_for_owner(
    session: AsyncSession, user_id: UUID, chain_id: UUID
) -> None:
    """Set the chain's latest email time from its emails."""
    latest = select(func.max(Email.sent_at)).where(Email.chain_id == chain_id).scalar_subquery()
    await session.execute(
        update(ReplyChain)
        .where(ReplyChain.user_id == user_id, ReplyChain.id == chain_id)
        .values(latest_email_at=latest)
    )


async def add_email_if_absent_for_owner(
    session: AsyncSession,
    user_id: UUID,
    *,
    chain_id: UUID,
    key: str,
    parsed: ParsedEmail,
    now: datetime,
) -> UUID | None:
    """Insert the email; `None` when another transaction stored the same key first."""
    statement = (
        insert(Email)
        .values(
            user_id=user_id,
            chain_id=chain_id,
            key=key,
            message_id=parsed.message_id,
            in_reply_to=parsed.in_reply_to,
            references=list(parsed.references),
            subject=parsed.subject,
            from_address=parsed.sender.address,
            from_name=parsed.sender.name,
            to_addresses=[address.model_dump() for address in parsed.to],
            cc_addresses=[address.model_dump() for address in parsed.cc],
            sent_at=parsed.sent_at,
            text=parsed.text,
            attachment_names=list(parsed.attachment_names),
            created_at=now,
        )
        .on_conflict_do_nothing(index_elements=[Email.user_id, Email.key])
        .returning(Email.id)
    )
    return (await session.execute(statement)).scalar_one_or_none()


async def add_copy_if_absent(
    session: AsyncSession, *, email_id: UUID, mailbox_id: UUID, folder_id: UUID, uid: int
) -> None:
    """Record that a folder holds a copy of the email; the same copy twice is ignored.

    Not owner-filtered: the caller got `email_id`, `mailbox_id` and `folder_id` from the owner's
    own rows.
    """
    statement = (
        insert(EmailCopy)
        .values(email_id=email_id, mailbox_id=mailbox_id, folder_id=folder_id, uid=uid)
        .on_conflict_do_nothing(index_elements=[EmailCopy.folder_id, EmailCopy.uid])
    )
    await session.execute(statement)


async def list_chains_page_for_owner(
    session: AsyncSession, user_id: UUID, *, after: Cursor | None, limit: int
) -> list[ChainRow]:
    """Chains, the latest email first (ties by id); `after` continues behind a cursor."""
    query = select(ReplyChain.id, ReplyChain.latest_email_at).where(ReplyChain.user_id == user_id)
    if after is not None:
        query = query.where(
            or_(
                ReplyChain.latest_email_at < after.moment,
                and_(ReplyChain.latest_email_at == after.moment, ReplyChain.id > after.id),
            )
        )
    query = query.order_by(ReplyChain.latest_email_at.desc(), ReplyChain.id).limit(limit)
    return [ChainRow(row.id, row.latest_email_at) for row in await session.execute(query)]


async def get_chain_for_owner(
    session: AsyncSession, user_id: UUID, chain_id: UUID
) -> ChainRow | None:
    """The user's chain, or `None` (also for another user's chain)."""
    row = (
        await session.execute(
            select(ReplyChain.id, ReplyChain.latest_email_at).where(
                ReplyChain.user_id == user_id, ReplyChain.id == chain_id
            )
        )
    ).one_or_none()
    return ChainRow(row.id, row.latest_email_at) if row is not None else None


async def count_emails_by_chain_for_owner(
    session: AsyncSession, user_id: UUID, chain_ids: Sequence[UUID]
) -> dict[UUID, int]:
    """The number of emails per chain."""
    rows = await session.execute(
        select(Email.chain_id, func.count())
        .where(Email.user_id == user_id, Email.chain_id.in_(chain_ids))
        .group_by(Email.chain_id)
    )
    return {chain_id: count for chain_id, count in rows}


async def get_first_subjects_for_owner(
    session: AsyncSession, user_id: UUID, chain_ids: Sequence[UUID]
) -> dict[UUID, str]:
    """The subject of the first (oldest) email of each chain."""
    rows = await session.execute(
        select(Email.chain_id, Email.subject)
        .where(Email.user_id == user_id, Email.chain_id.in_(chain_ids))
        .ext(distinct_on(Email.chain_id))
        .order_by(Email.chain_id, Email.sent_at, Email.id)
    )
    return {chain_id: subject for chain_id, subject in rows}


async def list_address_rows_for_owner(
    session: AsyncSession, user_id: UUID, chain_ids: Sequence[UUID]
) -> list[AddressRow]:
    """The addresses of every email of the chains, each chain's emails oldest first."""
    rows = await session.execute(
        select(
            Email.chain_id,
            Email.from_address,
            Email.from_name,
            Email.to_addresses,
            Email.cc_addresses,
        )
        .where(Email.user_id == user_id, Email.chain_id.in_(chain_ids))
        .order_by(Email.chain_id, Email.sent_at, Email.id)
    )
    return [AddressRow(*row) for row in rows]


async def list_emails_of_chain_for_owner(
    session: AsyncSession, user_id: UUID, chain_id: UUID, *, limit: int
) -> list[Email]:
    """The emails of a chain, oldest first, at most `limit`."""
    rows = await session.execute(
        select(Email)
        .where(Email.user_id == user_id, Email.chain_id == chain_id)
        .order_by(Email.sent_at, Email.id)
        .limit(limit)
    )
    return list(rows.scalars())
