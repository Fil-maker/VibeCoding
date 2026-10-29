"""FR-30, FR-31 through the HTTP API: listing and reading the reply chains."""

from datetime import datetime, timedelta
from http import HTTPStatus

from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader, FolderKind
from tests.factories import (
    ANNA_EMAIL,
    API,
    VERA_EMAIL,
    Factories,
    list_chains,
    list_mailboxes,
    open_chain,
)
from tests.mail_factory import INBOX, SENT, Attachment, numbered_email, raw_email

NEWLINE = chr(10)
YANDEX = "anna@yandex.ru"
OLEG = "Олег Смирнов <oleg@stroy.test>"
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"


async def anna_with_mailbox(factories: Factories) -> AsyncClient:
    """Анна signed in with anna@yandex.ru connected."""
    anna = await factories.signed_in(await factories.confirmed_user())
    await factories.connect_mailbox(anna, YANDEX)
    return anna


def body_text(number: int) -> str:
    """The two-line text of the number-th email of the contract chain."""
    return NEWLINE.join([f"Текст письма {number}", f"вторая строка {number}"])


def contract_chain(reader: FakeMailReader, now: datetime) -> None:
    """The chain «Договор поставки»: 4 emails with Олег, the latest one day ago, one attachment.

    The emails are put into the fake newest first, so reading order differs from sending order.
    """
    subject = "Договор поставки"

    def put(  # noqa: PLR0913 -- one call per email of the scenario
        folder: FolderKind,
        number: int,
        days_ago: int,
        *,
        sender: str,
        to: str,
        parent: str | None,
        files: list[Attachment] | None = None,
        cc: list[str] | None = None,
    ) -> None:
        reader.add(
            YANDEX,
            folder,
            raw_email(
                subject=subject if parent is None else "Re: " + subject,
                sender=sender,
                to=[to],
                cc=cc or [],
                sent_at=now - timedelta(days=days_ago),
                message_id=f"<c-{number}@stroy.test>",
                in_reply_to=parent,
                text=body_text(number),
                attachments=files or [],
            ),
        )

    put(INBOX, 4, 1, sender=OLEG, to=YANDEX, parent="<c-3@stroy.test>")
    attachment = [Attachment("договор.pdf")]
    put(INBOX, 3, 5, sender=OLEG, to=YANDEX, parent="<c-2@stroy.test>", files=attachment)
    put(SENT, 2, 9, sender=YANDEX, to="oleg@stroy.test", parent="<c-1@stroy.test>", cc=[ANNA_EMAIL])
    put(INBOX, 1, 10, sender=OLEG, to=YANDEX, parent=None)


# --- FR-30 List the reply chains ---


async def test_fr30_the_list_shows_the_latest_chain_first_with_participants_and_counts(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-30 «The list of chains»
    now = factories.clock.now()
    anna = await anna_with_mailbox(factories)
    contract_chain(reader, now)
    for number, days_ago in ((1, 12), (2, 9)):
        reader.add(
            YANDEX,
            INBOX,
            raw_email(
                subject="Смета",
                sender="ira@design.test",
                to=[YANDEX],
                sent_at=now - timedelta(days=days_ago),
                message_id=f"<e-{number}@design.test>",
                in_reply_to=None if number == 1 else "<e-1@design.test>",
            ),
        )
    await factories.read_due()

    chains = await list_chains(anna)

    assert [c["subject"] for c in chains] == ["Договор поставки", "Смета"]
    assert [c["email_count"] for c in chains] == [4, 2]
    assert [datetime.fromisoformat(c["latest_email_at"]) for c in chains] == [
        now - timedelta(days=1),
        now - timedelta(days=9),
    ]
    assert chains[0]["participants"] == [{"address": "oleg@stroy.test", "name": "Олег Смирнов"}]
    assert [p["address"] for p in chains[1]["participants"]] == ["ira@design.test"]
    assert set(chains[0]) == {"id", "subject", "participants", "email_count", "latest_email_at"}


async def test_fr30_the_users_own_addresses_are_not_participants(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-30: the own addresses are the logins of the mailboxes and the account email
    now = factories.clock.now()
    anna = await anna_with_mailbox(factories)
    contract_chain(reader, now)
    await factories.read_due()

    [chain] = await list_chains(anna)

    addresses = {p["address"] for p in chain["participants"]}
    assert addresses == {"oleg@stroy.test"}
    assert YANDEX not in addresses
    assert ANNA_EMAIL not in addresses


async def test_fr30_chains_come_in_pages_of_the_requested_size(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-30: 50 per page; the next page by the cursor
    now = factories.clock.now()
    anna = await anna_with_mailbox(factories)
    for number in range(3):
        reader.add(YANDEX, INBOX, numbered_email(number, now, days_ago=number + 1))
    await factories.read_due()

    first = (await anna.get(f"{API}/reply-chains", params={"limit": 2})).json()
    second = (
        await anna.get(f"{API}/reply-chains", params={"limit": 2, "cursor": first["next_cursor"]})
    ).json()

    assert [c["subject"] for c in first["items"]] == ["Письмо 0", "Письмо 1"]
    assert first["next_cursor"] is not None
    assert [c["subject"] for c in second["items"]] == ["Письмо 2"]
    assert second["next_cursor"] is None


async def test_fr30_a_page_holds_50_chains_by_default(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-30: 50 per page
    now = factories.clock.now()
    anna = await anna_with_mailbox(factories)
    for number in range(52):
        reader.add(YANDEX, INBOX, numbered_email(number, now, days_ago=number / 10 + 0.1))
    await factories.read_due()

    page = (await anna.get(f"{API}/reply-chains")).json()
    rest = (await anna.get(f"{API}/reply-chains", params={"cursor": page["next_cursor"]})).json()

    assert len(page["items"]) == 50
    assert len(rest["items"]) == 2
    assert rest["next_cursor"] is None


async def test_fr30_a_broken_cursor_is_refused(factories: Factories) -> None:
    # design «Interface»: 400 invalid_cursor
    anna = await anna_with_mailbox(factories)

    response = await anna.get(f"{API}/reply-chains", params={"cursor": "not-a-cursor"})

    assert response.status_code == HTTPStatus.BAD_REQUEST
    assert response.json()["error"]["code"] == "invalid_cursor"


async def test_fr30_a_user_without_mailboxes_has_no_chains(factories: Factories) -> None:
    # FR-30 «No emails yet»
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))

    response = await vera.get(f"{API}/reply-chains")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {"items": [], "next_cursor": None}


# --- FR-31 Read a reply chain ---


async def test_fr31_a_chain_shows_its_emails_from_the_oldest_to_the_newest(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-31 «Reading a chain»
    now = factories.clock.now()
    anna = await anna_with_mailbox(factories)
    contract_chain(reader, now)
    await factories.read_due()
    [summary] = await list_chains(anna)

    chain = await open_chain(anna, summary["id"])

    assert chain["subject"] == "Договор поставки"
    assert {p["address"] for p in chain["participants"]} == {"oleg@stroy.test"}
    emails = chain["emails"]
    assert [datetime.fromisoformat(e["sent_at"]) for e in emails] == [
        now - timedelta(days=days) for days in (10, 9, 5, 1)
    ]
    assert [e["subject"] for e in emails] == ["Договор поставки"] + ["Re: Договор поставки"] * 3
    senders = [(e["sender"]["address"], e["sender"]["name"]) for e in emails]
    assert senders == [
        ("oleg@stroy.test", "Олег Смирнов"),
        (YANDEX, None),
        ("oleg@stroy.test", "Олег Смирнов"),
        ("oleg@stroy.test", "Олег Смирнов"),
    ]
    assert [e["to"] for e in emails] == [
        [{"address": YANDEX, "name": None}],
        [{"address": "oleg@stroy.test", "name": None}],
        [{"address": YANDEX, "name": None}],
        [{"address": YANDEX, "name": None}],
    ]
    assert [e["cc"] for e in emails] == [[], [{"address": ANNA_EMAIL, "name": None}], [], []]
    assert [e["text"].strip() for e in emails] == [body_text(n) for n in (1, 2, 3, 4)]
    assert [e["attachment_names"] for e in emails] == [[], [], ["договор.pdf"], []]
    assert set(emails[0]) == {
        "id",
        "sender",
        "to",
        "cc",
        "sent_at",
        "subject",
        "text",
        "attachment_names",
    }


async def test_fr31_encoded_names_and_subjects_are_decoded(
    factories: Factories, reader: FakeMailReader
) -> None:
    # design «Text of an email»: addresses, names and subjects are decoded (RFC 2047)
    now = factories.clock.now()
    anna = await anna_with_mailbox(factories)
    reader.add(
        YANDEX,
        INBOX,
        b"From: =?utf-8?b?0J7Qu9C10LMg0KHQvNC40YDQvdC+0LI=?= <oleg@stroy.test>\r\n"
        b"To: anna@yandex.ru\r\n"
        b"Subject: =?utf-8?b?0JTQvtCz0L7QstC+0YA=?=\r\n"
        b"Message-ID: <enc-1@stroy.test>\r\n"
        b"Date: " + now.strftime("%a, %d %b %Y %H:%M:%S +0000").encode() + b"\r\n"
        b"Content-Type: text/plain; charset=utf-8\r\n\r\n"
        b"Hello\r\n",
    )
    await factories.read_due()
    [summary] = await list_chains(anna)

    chain = await open_chain(anna, summary["id"])

    assert chain["subject"] == "Договор"
    assert chain["emails"][0]["sender"] == {"address": "oleg@stroy.test", "name": "Олег Смирнов"}


async def test_fr31_an_html_only_email_is_shown_as_plain_text_without_scripts(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-31 «An HTML-only email»
    now = factories.clock.now()
    anna = await anna_with_mailbox(factories)
    reader.add(
        YANDEX,
        INBOX,
        raw_email(
            subject="Срок",
            sender=OLEG,
            to=[YANDEX],
            sent_at=now,
            message_id="<h-1@stroy.test>",
            text=None,
            html="<b>Срок</b> — пятница<script>alert(1)</script>",
        ),
    )
    await factories.read_due()
    [summary] = await list_chains(anna)

    chain = await open_chain(anna, summary["id"])

    text = chain["emails"][0]["text"]
    assert text.strip() == "Срок — пятница"
    assert "<" not in text
    assert "alert" not in text


async def test_fr31_html_entities_are_decoded_in_the_text(
    factories: Factories, reader: FakeMailReader
) -> None:
    # design «Text of an email»: entities decoded, style dropped
    now = factories.clock.now()
    anna = await anna_with_mailbox(factories)
    reader.add(
        YANDEX,
        INBOX,
        raw_email(
            subject="Цена",
            sender=OLEG,
            to=[YANDEX],
            sent_at=now,
            message_id="<h-2@stroy.test>",
            text=None,
            html="<p>Tom &amp; Jerry</p><style>p { color: red }</style>",
        ),
    )
    await factories.read_due()
    [summary] = await list_chains(anna)

    chain = await open_chain(anna, summary["id"])

    assert chain["emails"][0]["text"].strip() == "Tom & Jerry"


async def test_fr31_another_users_chain_is_not_found(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-31 «Another user's chain»
    now = factories.clock.now()
    anna = await anna_with_mailbox(factories)
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))
    reader.add(YANDEX, INBOX, numbered_email(1, now))
    await factories.read_due()
    [summary] = await list_chains(anna)

    foreign = await vera.get(f"{API}/reply-chains/{summary['id']}")
    unknown = await vera.get(f"{API}/reply-chains/{UNKNOWN_ID}")

    assert foreign.status_code == HTTPStatus.NOT_FOUND
    assert foreign.json()["error"]["code"] == "not_found"
    assert foreign.json() == unknown.json()
    assert "Письмо 1" not in foreign.text


async def test_fr30_the_logins_of_all_mailboxes_are_not_participants(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-30: the own addresses are the logins of their mailboxes (all of them)
    now = factories.clock.now()
    anna = await anna_with_mailbox(factories)
    await factories.connect_mailbox(anna, "anna@mail.ru", server="imap.mail.ru")
    reader.add(
        YANDEX,
        INBOX,
        raw_email(
            subject="Общее письмо",
            sender=OLEG,
            to=[YANDEX, "anna@mail.ru"],
            sent_at=now,
            message_id="<two-1@stroy.test>",
        ),
    )
    await factories.read_due()

    [chain] = await list_chains(anna)

    addresses = {p["address"] for p in chain["participants"]}
    assert addresses == {"oleg@stroy.test"}
    assert "anna@mail.ru" not in addresses


async def test_fr30_a_reply_moves_an_older_chain_to_the_top(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-30: the chain with the latest email first
    now = factories.clock.now()
    anna = await anna_with_mailbox(factories)
    reader.add(YANDEX, INBOX, numbered_email(1, now, days_ago=10))
    reader.add(YANDEX, INBOX, numbered_email(2, now, days_ago=5))
    await factories.read_due()
    before = await list_chains(anna)
    assert [c["subject"] for c in before] == ["Письмо 2", "Письмо 1"]
    reader.add(
        YANDEX,
        INBOX,
        raw_email(
            subject="Re: Письмо 1",
            sender=OLEG,
            to=[YANDEX],
            sent_at=now - timedelta(days=1),
            message_id="<m1-reply@stroy.test>",
            in_reply_to="<m1@stroy.test>",
        ),
    )
    for mailbox in await list_mailboxes(anna):
        await anna.post(f"{API}/mailboxes/{mailbox['id']}/refresh")
    await factories.read_due()

    after = await list_chains(anna)

    assert [c["subject"] for c in after] == ["Письмо 1", "Письмо 2"]
    assert [c["email_count"] for c in after] == [2, 1]
    assert datetime.fromisoformat(after[0]["latest_email_at"]) == now - timedelta(days=1)
