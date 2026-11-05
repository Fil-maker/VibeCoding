"""FR-31 through the HTTP API: the attachments of an email in a reply chain."""

from typing import Any

from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from tests.factories import Factories, list_chains, open_chain
from tests.mail_factory import INBOX, raw_email, sized_attachment

YANDEX = "anna@yandex.ru"
OLEG = "Олег Смирнов <oleg@stroy.test>"


async def read_single_email(
    factories: Factories, reader: FakeMailReader, files: list[Any]
) -> tuple[AsyncClient, dict[str, Any]]:
    """Анна with one read email carrying `files`; returns her client and the email as shown."""
    now = factories.clock.now()
    anna = await factories.signed_in(await factories.confirmed_user())
    await factories.connect_mailbox(anna, YANDEX)
    reader.add(
        YANDEX,
        INBOX,
        raw_email(
            subject="Вложения",
            sender=OLEG,
            to=[YANDEX],
            sent_at=now,
            message_id="<att-1@stroy.test>",
            attachments=files,
        ),
    )
    await factories.read_due()
    [summary] = await list_chains(anna)
    [email] = (await open_chain(anna, summary["id"]))["emails"]
    return anna, email


async def test_fr31_small_and_nameless_types_keep_their_exact_sizes(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-31 «Small and nameless types»
    files = [sized_attachment("смета.xlsx", 812), sized_attachment("README", 45_000)]

    _, email = await read_single_email(factories, reader, files)

    assert email["attachments"] == [
        {"index": 0, "name": "смета.xlsx", "size": 812},
        {"index": 1, "name": "README", "size": 45_000},
    ]


async def test_fr31_two_files_with_one_name_have_their_own_positions_and_sizes(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-31 «Reading a chain»: the list keeps both files of one name, each with its position
    files = [sized_attachment("скан.jpg", 100), sized_attachment("скан.jpg", 250)]

    _, email = await read_single_email(factories, reader, files)

    assert email["attachments"] == [
        {"index": 0, "name": "скан.jpg", "size": 100},
        {"index": 1, "name": "скан.jpg", "size": 250},
    ]


async def test_fr31_a_part_without_a_name_is_not_an_attachment(
    factories: Factories, reader: FakeMailReader
) -> None:
    # design «Context» (parsing rule): only parts with a name are listed, counted from 0
    files = [sized_attachment("", 10), sized_attachment("договор.pdf", 20, subtype="pdf")]

    _, email = await read_single_email(factories, reader, files)

    assert email["attachments"] == [{"index": 0, "name": "договор.pdf", "size": 20}]


async def test_fr31_an_email_without_files_has_an_empty_list(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-31 «Reading a chain»: the emails that carried no file show none
    _, email = await read_single_email(factories, reader, [])

    assert email["attachments"] == []
