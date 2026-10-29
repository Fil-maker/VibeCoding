"""Use cases of correspondence: storing read emails, listing and reading reply chains."""

from collections.abc import Sequence
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from pydantic import TypeAdapter
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.accounts import repository as accounts_repository
from app.modules.correspondence import repository
from app.modules.correspondence.domain import (
    ChainRef,
    ParsedEmail,
    choose_surviving_chain,
    email_key,
    own_address_set,
    parse_raw_message,
)
from app.modules.correspondence.models import Email
from app.modules.correspondence.repository import AddressRow
from app.modules.correspondence.schemas import Address, EmailView, ReplyChain, ReplyChainSummary
from app.modules.mailboxes import repository as mailboxes_repository
from app.platform.auth_context import AuthContext
from app.platform.db import get_database_session
from app.platform.errors import NotFound
from app.platform.mail_reader import RawMessage
from app.platform.pagination import (
    Cursor,
    Page,
    decode_cursor,
    encode_cursor,
)

CHAIN_EMAIL_LIMIT = 500
ADDRESS_LIST = TypeAdapter(list[Address])


async def _join_chain(
    session: AsyncSession, user_id: UUID, key: str, parsed: ParsedEmail, now: datetime
) -> tuple[UUID, bool]:
    """The chain the new email belongs to and whether it was just created.

    All chains of the emails it names and of the stored emails naming it become one: the oldest
    survives, so the result does not depend on the reading order.
    """
    chain_ids = set(
        await repository.list_chain_ids_of_keys_for_owner(session, user_id, parsed.related_keys)
    )
    if parsed.message_id is not None:
        chain_ids.update(
            await repository.list_chain_ids_naming_key_for_owner(session, user_id, key)
        )
    chains: list[ChainRef] = await repository.lock_chains_for_owner(
        session, user_id, list(chain_ids)
    )
    if not chains:
        chain_id = await repository.add_chain_for_owner(
            session, user_id, latest_email_at=parsed.sent_at, now=now
        )
        return chain_id, True
    survivor = choose_surviving_chain(chains)
    others = [chain.id for chain in chains if chain.id != survivor.id]
    if others:
        await repository.move_emails_to_chain_for_owner(session, user_id, others, survivor.id)
    return survivor.id, False


async def _store_one(
    session: AsyncSession,
    user_id: UUID,
    *,
    mailbox_id: UUID,
    folder_id: UUID,
    uidvalidity: int,
    message: RawMessage,
    now: datetime,
) -> bool:
    parsed = parse_raw_message(message.data, message.internal_date)
    key = email_key(
        parsed, mailbox_id=mailbox_id, folder_id=folder_id, uidvalidity=uidvalidity, uid=message.uid
    )
    stored = await repository.get_email_by_key_for_owner(session, user_id, key)
    if stored is None:
        chain_id, is_new_chain = await _join_chain(session, user_id, key, parsed, now)
        email_id = await repository.add_email_if_absent_for_owner(
            session, user_id, chain_id=chain_id, key=key, parsed=parsed, now=now
        )
        if email_id is not None:
            await repository.refresh_chain_latest_email_at_for_owner(session, user_id, chain_id)
            await _add_copy(session, email_id, mailbox_id, folder_id, message.uid)
            return True
        # Another transaction stored the same email first: keep its chain, only add the copy.
        if is_new_chain:
            await repository.delete_chain_for_owner(session, user_id, chain_id)
        stored = await repository.get_email_by_key_for_owner(session, user_id, key)
    if stored is not None:
        await _add_copy(session, stored.id, mailbox_id, folder_id, message.uid)
    return False


async def _add_copy(
    session: AsyncSession, email_id: UUID, mailbox_id: UUID, folder_id: UUID, uid: int
) -> None:
    await repository.add_copy_if_absent(
        session, email_id=email_id, mailbox_id=mailbox_id, folder_id=folder_id, uid=uid
    )


async def store_raw_messages(
    session: AsyncSession,
    *,
    user_id: UUID,
    mailbox_id: UUID,
    folder_id: UUID,
    uidvalidity: int,
    messages: Sequence[RawMessage],
    now: datetime,
) -> int:
    """Store a batch read from one folder of one mailbox; return how many emails were new.

    Called by the mailboxes service inside its own transaction (`async with session.begin()`),
    so the batch and the folder's `last_uid` commit together; nothing is committed here. An email
    already stored for the user only gains a copy. `user_id` must be the mailbox's owner.
    """
    added = 0
    for message in sorted(messages, key=lambda item: item.uid):
        if await _store_one(
            session,
            user_id,
            mailbox_id=mailbox_id,
            folder_id=folder_id,
            uidvalidity=uidvalidity,
            message=message,
            now=now,
        ):
            added += 1
    return added


async def _own_addresses(session: AsyncSession, user_id: UUID) -> frozenset[str]:
    logins = await mailboxes_repository.list_logins_for_owner(session, user_id)
    account = await accounts_repository.find_by_id(session, user_id)
    return own_address_set([*logins, *([account.email] if account is not None else [])])


def _participants(rows: Sequence[AddressRow], own: frozenset[str]) -> dict[UUID, list[Address]]:
    """Distinct addresses per chain in order of first appearance, the user's own left out."""
    found: dict[UUID, dict[str, Address]] = {}
    for row in rows:
        people = [Address(address=row.from_address, name=row.from_name)]
        people += ADDRESS_LIST.validate_python(row.to_addresses)
        people += ADDRESS_LIST.validate_python(row.cc_addresses)
        chain = found.setdefault(row.chain_id, {})
        for person in people:
            if person.address and person.address not in own:
                known = chain.get(person.address)
                if known is None or (known.name is None and person.name is not None):
                    chain[person.address] = person
    return {chain_id: list(people.values()) for chain_id, people in found.items()}


async def list_reply_chains(
    session: AsyncSession, context: AuthContext, *, limit: int, cursor: str | None
) -> Page[ReplyChainSummary]:
    """A page of the user's chains, the latest email first. Raises `InvalidCursor`."""
    after = decode_cursor(cursor) if cursor is not None else None
    async with session.begin():
        rows = await repository.list_chains_page_for_owner(
            session, context.user_id, after=after, limit=limit + 1
        )
        page = rows[:limit]
        ids = [row.id for row in page]
        counts = await repository.count_emails_by_chain_for_owner(session, context.user_id, ids)
        subjects = await repository.get_first_subjects_for_owner(session, context.user_id, ids)
        address_rows = await repository.list_address_rows_for_owner(session, context.user_id, ids)
        participants = _participants(address_rows, await _own_addresses(session, context.user_id))
    items = [
        ReplyChainSummary(
            id=row.id,
            subject=subjects.get(row.id, ""),
            participants=participants.get(row.id, []),
            email_count=counts.get(row.id, 0),
            latest_email_at=row.latest_email_at,
        )
        for row in page
    ]
    last = page[-1] if len(rows) > limit else None
    next_cursor = (
        encode_cursor(Cursor(moment=last.latest_email_at, id=last.id)) if last is not None else None
    )
    return Page[ReplyChainSummary](items=items, next_cursor=next_cursor)


def _email_view(email: Email) -> EmailView:
    return EmailView(
        id=email.id,
        sender=Address(address=email.from_address, name=email.from_name),
        to=ADDRESS_LIST.validate_python(email.to_addresses),
        cc=ADDRESS_LIST.validate_python(email.cc_addresses),
        sent_at=email.sent_at,
        subject=email.subject,
        text=email.text,
        attachment_names=email.attachment_names,
    )


async def get_reply_chain(
    session: AsyncSession, context: AuthContext, chain_id: UUID
) -> ReplyChain:
    """A chain of the user with its emails; `NotFound` for another user's or an unknown id."""
    async with session.begin():
        chain = await repository.get_chain_for_owner(session, context.user_id, chain_id)
        if chain is None:
            raise NotFound
        emails = await repository.list_emails_of_chain_for_owner(
            session, context.user_id, chain_id, limit=CHAIN_EMAIL_LIMIT
        )
        address_rows = await repository.list_address_rows_for_owner(
            session, context.user_id, [chain_id]
        )
        participants = _participants(address_rows, await _own_addresses(session, context.user_id))
    return ReplyChain(
        id=chain_id,
        subject=emails[0].subject if emails else "",
        participants=participants.get(chain_id, []),
        emails=[_email_view(email) for email in emails],
    )


class CorrespondenceService:
    """The read use cases of correspondence bound to one database session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_reply_chains(
        self, context: AuthContext, *, limit: int, cursor: str | None
    ) -> Page[ReplyChainSummary]:
        """See `list_reply_chains`."""
        return await list_reply_chains(self._session, context, limit=limit, cursor=cursor)

    async def get_reply_chain(self, context: AuthContext, chain_id: UUID) -> ReplyChain:
        """See `get_reply_chain`."""
        return await get_reply_chain(self._session, context, chain_id)


def get_correspondence_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> CorrespondenceService:
    """Dependency factory of the correspondence use cases."""
    return CorrespondenceService(session)
