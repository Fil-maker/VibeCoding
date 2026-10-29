"""FR-28, FR-29 through the HTTP API and `read_due_mailboxes`: one email once, joined chains."""

from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from tests.factories import (
    API,
    VERA_EMAIL,
    Factories,
    count_emails,
    list_chains,
    list_mailboxes,
    open_chain,
)
from tests.mail_factory import INBOX, SENT, numbered_email, raw_email

YANDEX = "anna@yandex.ru"
MAILRU = "anna@mail.ru"
OLEG = "Олег <oleg@stroy.test>"


async def anna_with_two_mailboxes(factories: Factories) -> AsyncClient:
    """Анна signed in with anna@yandex.ru and anna@mail.ru connected."""
    anna = await factories.signed_in(await factories.confirmed_user())
    await factories.connect_mailbox(anna, YANDEX, server="imap.yandex.ru")
    await factories.connect_mailbox(anna, MAILRU, server="imap.mail.ru")
    return anna


async def chain_sizes(client: AsyncClient) -> list[int]:
    """The email counts of the chains, largest first."""
    return sorted((c["email_count"] for c in await list_chains(client)), reverse=True)


# --- FR-28 Every email is stored once ---


async def test_fr28_an_email_in_two_mailboxes_is_shown_once(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-28 «An email in two mailboxes»
    now = factories.clock.now()
    anna = await anna_with_two_mailboxes(factories)
    sent = raw_email(
        subject="Заметка",
        sender=YANDEX,
        to=[MAILRU],
        sent_at=now,
        message_id="<note-1@yandex.ru>",
    )
    reader.add(YANDEX, SENT, sent)
    reader.add(MAILRU, INBOX, sent)

    await factories.read_due()

    [chain] = await list_chains(anna)
    assert chain["email_count"] == 1
    assert len((await open_chain(anna, chain["id"]))["emails"]) == 1


async def test_fr28_the_same_email_in_inbox_and_sent_of_one_mailbox_is_stored_once(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-28: however many of the folders hold it
    now = factories.clock.now()
    anna = await anna_with_two_mailboxes(factories)
    note = raw_email(
        subject="Себе", sender=YANDEX, to=[YANDEX], sent_at=now, message_id="<self-1@yandex.ru>"
    )
    reader.add(YANDEX, SENT, note)
    reader.add(YANDEX, INBOX, note)

    await factories.read_due()

    assert await count_emails(anna) == 1


async def test_fr28_an_email_without_message_id_counts_once_only_within_its_folder(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-28: without a Message-ID one email only within the folder it was read from
    now = factories.clock.now()
    anna = await anna_with_two_mailboxes(factories)
    anonymous = raw_email(
        subject="Без идентификатора",
        sender="oleg@stroy.test",
        to=[YANDEX, MAILRU],
        sent_at=now,
        message_id=None,
    )
    reader.add(YANDEX, INBOX, anonymous)
    reader.add(MAILRU, INBOX, anonymous)
    await factories.read_due()
    assert await count_emails(anna) == 2

    for mailbox in await list_mailboxes(anna):
        await anna.post(f"{API}/mailboxes/{mailbox['id']}/refresh")
    await factories.read_due()

    assert await count_emails(anna) == 2


async def test_fr28_two_users_receiving_the_same_email_each_see_it_once(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-28 «Two users receive the same email»
    now = factories.clock.now()
    anna = await factories.signed_in(await factories.confirmed_user())
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))
    await factories.connect_mailbox(anna, YANDEX)
    await factories.connect_mailbox(vera, "vera@yandex.ru")
    shared = raw_email(
        subject="Смета",
        sender=OLEG,
        to=[YANDEX, "vera@yandex.ru"],
        sent_at=now,
        message_id="<shared-1@stroy.test>",
    )
    reader.add(YANDEX, INBOX, shared)
    reader.add("vera@yandex.ru", INBOX, shared)

    await factories.read_due()

    for reader_of_chain in (anna, vera):
        [chain] = await list_chains(reader_of_chain)
        assert chain["subject"] == "Смета"
        assert chain["email_count"] == 1
        opened = await open_chain(reader_of_chain, chain["id"])
        assert [e["subject"] for e in opened["emails"]] == ["Смета"]
    [anna_chain] = await list_chains(anna)
    [vera_chain] = await list_chains(vera)
    assert anna_chain["id"] != vera_chain["id"]


async def test_fr28_a_chain_never_lists_the_other_users_participants_or_emails(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-28 «Two users receive the same email»: the chain lists only the own participants
    # and emails of its user
    now = factories.clock.now()
    anna = await factories.signed_in(await factories.confirmed_user())
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))
    await factories.connect_mailbox(anna, YANDEX)
    await factories.connect_mailbox(vera, "vera@yandex.ru")
    shared = raw_email(
        subject="Смета",
        sender=OLEG,
        to=[YANDEX, "vera@yandex.ru"],
        sent_at=now,
        message_id="<shared-1@stroy.test>",
    )
    reader.add(YANDEX, INBOX, shared)
    reader.add("vera@yandex.ru", INBOX, shared)
    private_reply = raw_email(
        subject="Re: Смета",
        sender=YANDEX,
        to=["oleg@stroy.test"],
        cc=["secret@anna-only.test"],
        sent_at=now,
        message_id="<shared-2@yandex.ru>",
        in_reply_to="<shared-1@stroy.test>",
    )
    reader.add(YANDEX, SENT, private_reply)

    await factories.read_due()

    [anna_chain] = await list_chains(anna)
    [vera_chain] = await list_chains(vera)
    assert anna_chain["email_count"] == 2
    assert vera_chain["email_count"] == 1
    assert anna_chain["id"] != vera_chain["id"]
    opened = await open_chain(vera, vera_chain["id"])
    assert len(opened["emails"]) == 1
    assert "secret@anna-only.test" not in str(opened)
    assert "secret@anna-only.test" not in str(vera_chain)
    assert {p["address"] for p in vera_chain["participants"]} == {
        "anna@yandex.ru",
        "oleg@stroy.test",
    }


# --- FR-29 Join emails into reply chains ---


async def test_fr29_a_reply_from_another_mailbox_joins_the_chain(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-29 «A reply from another mailbox joins the chain»
    now = factories.clock.now()
    anna = await anna_with_two_mailboxes(factories)
    reader.add(
        YANDEX,
        INBOX,
        raw_email(
            subject="Договор",
            sender=OLEG,
            to=[YANDEX],
            sent_at=now,
            message_id="<d-1@stroy.test>",
        ),
    )
    reader.add(
        MAILRU,
        SENT,
        raw_email(
            subject="Re: Договор",
            sender=MAILRU,
            to=["oleg@stroy.test"],
            sent_at=now,
            message_id="<d-2@mail.ru>",
            in_reply_to="<d-1@stroy.test>",
        ),
    )

    await factories.read_due()

    assert await chain_sizes(anna) == [2]


async def test_fr29_a_reply_read_before_its_original_joins_it_at_a_later_read(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-29 «A reply read before its original»
    now = factories.clock.now()
    anna = await anna_with_two_mailboxes(factories)
    reader.add(
        MAILRU,
        SENT,
        raw_email(
            subject="Re: Договор",
            sender=MAILRU,
            to=["oleg@stroy.test"],
            sent_at=now,
            message_id="<d-2@mail.ru>",
            in_reply_to="<d-1@stroy.test>",
        ),
    )
    await factories.read_due()
    assert await chain_sizes(anna) == [1]
    reader.add(
        YANDEX,
        INBOX,
        raw_email(
            subject="Договор",
            sender=OLEG,
            to=[YANDEX],
            sent_at=now,
            message_id="<d-1@stroy.test>",
        ),
    )
    for mailbox in await list_mailboxes(anna):
        await anna.post(f"{API}/mailboxes/{mailbox['id']}/refresh")

    await factories.read_due()

    assert await chain_sizes(anna) == [2]


async def test_fr29_an_email_naming_two_chains_joins_them(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-29 «An email links two chains»
    now = factories.clock.now()
    anna = await anna_with_two_mailboxes(factories)
    reader.add(YANDEX, INBOX, numbered_email(1, now, days_ago=3))
    reader.add(YANDEX, INBOX, numbered_email(2, now, days_ago=2))
    await factories.read_due()
    assert await chain_sizes(anna) == [1, 1]
    reader.add(
        YANDEX,
        INBOX,
        raw_email(
            subject="Объединяем",
            sender=OLEG,
            to=[YANDEX],
            sent_at=now,
            message_id="<link-1@stroy.test>",
            references=["<m1@stroy.test>", "<m2@stroy.test>"],
        ),
    )
    for mailbox in await list_mailboxes(anna):
        await anna.post(f"{API}/mailboxes/{mailbox['id']}/refresh")

    await factories.read_due()

    [chain] = await list_chains(anna)
    assert chain["email_count"] == 3


async def test_fr29_the_same_subject_without_reply_headers_makes_two_chains(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-29 «The same subject without reply headers»
    now = factories.clock.now()
    anna = await anna_with_two_mailboxes(factories)
    for number, sender in enumerate(["oleg@stroy.test", "ira@design.test"]):
        reader.add(
            YANDEX,
            INBOX,
            raw_email(
                subject="Смета на 2027 год",
                sender=sender,
                to=[YANDEX],
                sent_at=now,
                message_id=f"<s-{number}@stroy.test>",
            ),
        )

    await factories.read_due()

    chains = await list_chains(anna)
    assert [c["subject"] for c in chains] == ["Смета на 2027 год", "Смета на 2027 год"]
    assert await chain_sizes(anna) == [1, 1]
    assert chains[0]["id"] != chains[1]["id"]
