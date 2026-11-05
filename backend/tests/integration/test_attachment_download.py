"""FR-57, FR-58, FR-25 through the HTTP API: downloading an attachment from the mailbox."""

from collections.abc import Generator
from contextlib import contextmanager
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any
from unittest.mock import AsyncMock, patch
from urllib.parse import unquote

from httpx import AsyncClient
from sqlalchemy import create_engine, text

from app.platform.mail_reader import FakeMailReader
from tests.factories import (
    API,
    VERA_EMAIL,
    Factories,
    count_emails,
    download_attachment,
    download_attachment_response,
    list_chains,
    list_mailboxes,
    open_chain,
)
from tests.mail_factory import (
    INBOX,
    SENT,
    Attachment,
    raw_email,
    remove_from_mailbox,
    replace_in_mailbox,
    sized_attachment,
)

YANDEX = "anna@yandex.ru"
MAILRU = "anna@mail.ru"
OLEG = "Олег Смирнов <oleg@stroy.test>"
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"
CONTRACT = sized_attachment("договор.pdf", 5000, subtype="pdf")
SAVING = "attachment; filename*=UTF-8" + chr(39) + chr(39)
DISCONNECTED = {
    "error": {"code": "mailbox_disconnected", "message": "Файл недоступен: ящик отключён"}
}
GONE = {"error": {"code": "email_gone", "message": "Письмо больше не найдено в ящике"}}
SIGN_IN_FAILED = {
    "error": {
        "code": "mailbox_sign_in_failed",
        "message": "Не удалось получить файл: не удалось войти в ящик",
    }
}
UNREACHABLE = {
    "error": {
        "code": "mailbox_unreachable",
        "message": "Не удалось получить файл: сервер не отвечает",
    }
}


def message_with(files: list[Attachment], factories: Factories) -> bytes:
    """The email of the scenarios: one Message-ID, so a second mailbox holds the same email."""
    return raw_email(
        subject="Договор поставки",
        sender=OLEG,
        to=[YANDEX],
        sent_at=factories.clock.now(),
        message_id="<dl-1@stroy.test>",
        attachments=files,
    )


async def anna_with_email(
    factories: Factories, reader: FakeMailReader, files: list[Attachment]
) -> tuple[AsyncClient, str]:
    """Анна with anna@yandex.ru holding one read email with `files`; returns client, email id."""
    anna = await factories.signed_in(await factories.confirmed_user())
    await factories.connect_mailbox(anna, YANDEX)
    reader.add(YANDEX, INBOX, message_with(files, factories))
    await factories.read_due()
    return anna, await only_email_id(anna)


async def only_email_id(client: AsyncClient) -> str:
    """The id of the one email of the user."""
    [summary] = await list_chains(client)
    [email] = (await open_chain(client, summary["id"]))["emails"]
    return str(email["id"])


@dataclass
class ReaderSpies:
    """Every call of the reader's methods made while watching."""

    check: AsyncMock
    fetch: AsyncMock
    fetch_message: AsyncMock

    def total(self) -> int:
        """How many times the app reached for the mailbox at all."""
        return self.check.await_count + self.fetch.await_count + self.fetch_message.await_count


@contextmanager
def watching(reader: FakeMailReader) -> Generator[ReaderSpies]:
    """Record every call of the reader (`check`, `fetch`, `fetch_message`) while letting it work."""
    with (
        patch.object(reader, "check", wraps=reader.check) as check,
        patch.object(reader, "fetch", wraps=reader.fetch) as fetch,
        patch.object(reader, "fetch_message", wraps=reader.fetch_message) as fetch_message,  # pyright: ignore[reportAttributeAccessIssue] -- the method is new
    ):
        yield ReaderSpies(check, fetch, fetch_message)


def login_of(call: Any) -> str:
    """The login of the credentials a `fetch_message` call was made with."""
    credentials = call.args[0] if call.args else call.kwargs["credentials"]
    return str(credentials.login)


def everything_stored(url: str) -> str:
    """Every row of every table of the test database as one text."""
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            names = list(
                conn.execute(
                    text("SELECT tablename FROM pg_tables WHERE schemaname = 'public'")
                ).scalars()
            )
            rows = [
                str(conn.execute(text(f'SELECT t::text FROM "{name}" t')).scalars().all())
                for name in names
            ]
            return "\n".join(rows)
    finally:
        engine.dispose()


# --- FR-57 Download an attachment ---


async def test_fr57_a_download_gives_the_file_bytes_under_its_own_name_and_always_for_saving(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-57 «Downloading a contract»
    anna, email_id = await anna_with_email(factories, reader, [CONTRACT])

    response = await download_attachment_response(anna, email_id, 0)

    assert response.status_code == HTTPStatus.OK
    assert response.content == CONTRACT.content
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["x-content-type-options"] == "nosniff"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith(SAVING)
    assert unquote(disposition.removeprefix(SAVING)) == "договор.pdf"


async def test_fr57_the_second_of_two_files_with_one_name_is_the_one_downloaded(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-57 «Two attachments with one name»
    first = Attachment("скан.jpg", content=b"first-scan", maintype="image", subtype="jpeg")
    second = Attachment("скан.jpg", content=b"second-scan", maintype="image", subtype="jpeg")
    anna, email_id = await anna_with_email(factories, reader, [first, second])

    assert await download_attachment(anna, email_id, 1) == b"second-scan"
    assert await download_attachment(anna, email_id, 0) == b"first-scan"


async def test_fr57_the_file_comes_from_the_connected_mailbox_when_the_other_is_disconnected(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-57 «The email is in two mailboxes, one disconnected»
    anna = await factories.signed_in(await factories.confirmed_user())
    yandex = await factories.connect_mailbox(anna, YANDEX)
    await factories.connect_mailbox(anna, MAILRU, server="imap.mail.ru")
    raw = message_with([CONTRACT], factories)
    reader.add(YANDEX, INBOX, raw)
    reader.add(MAILRU, INBOX, raw)
    await factories.read_due()
    email_id = await only_email_id(anna)
    await anna.delete(f"{API}/mailboxes/{yandex['id']}")

    with watching(reader) as spy:
        content = await download_attachment(anna, email_id, 0)

    assert content == CONTRACT.content
    assert spy.fetch_message.await_count >= 1
    assert {login_of(call) for call in spy.fetch_message.await_args_list} == {MAILRU}


async def test_fr57_two_downloads_give_the_same_file_and_the_app_keeps_no_copy(
    factories: Factories, reader: FakeMailReader, test_database_url: str
) -> None:
    # FR-57 «Downloading twice»
    marker = b"UNIQUE-ATTACHMENT-CONTENT-7f3a9c"
    unique = Attachment("договор.pdf", content=marker, subtype="pdf")
    anna, email_id = await anna_with_email(factories, reader, [unique])

    first = await download_attachment(anna, email_id, 0)
    second = await download_attachment(anna, email_id, 0)

    stored = everything_stored(test_database_url)
    assert first == second == marker
    assert marker.decode() not in stored
    assert "VU5JUVVFLUFUVEFDSE1FTlQ" not in stored  # the base64 of the marker


async def test_fr57_an_html_attachment_is_saved_never_opened_in_the_app(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-57 «An HTML attachment»
    page = Attachment(
        "счёт.html", content=b"<script>alert(1)</script>", maintype="text", subtype="html"
    )
    anna, email_id = await anna_with_email(factories, reader, [page])

    response = await download_attachment_response(anna, email_id, 0)

    assert response.status_code == HTTPStatus.OK
    assert response.content == b"<script>alert(1)</script>"
    assert response.headers["content-type"] == "application/octet-stream"
    assert response.headers["x-content-type-options"] == "nosniff"
    disposition = response.headers["content-disposition"]
    assert disposition.startswith(SAVING)
    assert unquote(disposition.removeprefix(SAVING)) == "счёт.html"


async def test_fr57_another_users_attachment_is_not_found_and_no_mailbox_is_contacted(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-57 «Another user's attachment»
    _, email_id = await anna_with_email(factories, reader, [CONTRACT])
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))

    with watching(reader) as spy:
        foreign = await download_attachment_response(vera, email_id, 0)
        unknown = await download_attachment_response(vera, UNKNOWN_ID, 0)

    assert foreign.status_code == HTTPStatus.NOT_FOUND
    assert foreign.json()["error"]["code"] == "not_found"
    assert foreign.json() == unknown.json()
    assert CONTRACT.content not in foreign.content
    assert spy.total() == 0


async def test_fr57_an_index_out_of_range_is_not_found_and_no_mailbox_is_contacted(
    factories: Factories, reader: FakeMailReader
) -> None:
    # design «Interface»: 404 for an index out of range
    anna, email_id = await anna_with_email(factories, reader, [CONTRACT])

    with watching(reader) as spy:
        response = await download_attachment_response(anna, email_id, 1)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["error"]["code"] == "not_found"
    assert spy.total() == 0


async def test_fr57_signed_out_nobody_downloads(
    factories: Factories, reader: FakeMailReader
) -> None:
    # design «Interface»: 401 when signed out
    _, email_id = await anna_with_email(factories, reader, [CONTRACT])
    stranger = await factories.open_client()

    response = await download_attachment_response(stranger, email_id, 0)

    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert CONTRACT.content not in response.content


# --- FR-58 An attachment that cannot be fetched ---


async def test_fr58_no_connected_mailbox_holds_the_email(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-58 «No connected mailbox holds the email»
    anna, email_id = await anna_with_email(factories, reader, [CONTRACT])
    [mailbox] = await list_mailboxes(anna)
    await anna.delete(f"{API}/mailboxes/{mailbox['id']}")
    before = await list_mailboxes(anna)

    response = await download_attachment_response(anna, email_id, 0)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json() == DISCONNECTED
    assert await list_mailboxes(anna) == before
    assert CONTRACT.content not in response.content


async def test_fr58_the_email_is_gone_from_the_mailbox(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-58 «The email is gone from the mailbox»
    anna, email_id = await anna_with_email(factories, reader, [CONTRACT])
    remove_from_mailbox(reader, YANDEX, INBOX)
    before = await list_mailboxes(anna)

    response = await download_attachment_response(anna, email_id, 0)

    assert response.status_code == HTTPStatus.GONE
    assert response.json() == GONE
    assert await list_mailboxes(anna) == before
    assert await count_emails(anna) == 1


async def test_fr58_a_refused_sign_in_leaves_the_mailbox_status_as_it_was(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-58 «The server refuses the sign-in»
    anna, email_id = await anna_with_email(factories, reader, [CONTRACT])
    before = await list_mailboxes(anna)
    reader.fail_sign_in(YANDEX)

    response = await download_attachment_response(anna, email_id, 0)

    assert response.status_code == HTTPStatus.BAD_GATEWAY
    assert response.json() == SIGN_IN_FAILED
    assert await list_mailboxes(anna) == before


async def test_fr58_an_unreachable_server_leaves_the_status_and_a_later_click_downloads(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-58 «The server does not answer»
    anna, email_id = await anna_with_email(factories, reader, [CONTRACT])
    before = await list_mailboxes(anna)
    reader.make_unreachable("imap.yandex.ru")

    failed = await download_attachment_response(anna, email_id, 0)
    reader.restore("imap.yandex.ru")
    later = await download_attachment_response(anna, email_id, 0)

    assert failed.status_code == HTTPStatus.GATEWAY_TIMEOUT
    assert failed.json() == UNREACHABLE
    assert await list_mailboxes(anna) == before
    assert later.status_code == HTTPStatus.OK
    assert later.content == CONTRACT.content


# --- FR-25 Reading never changes the mailbox ---


async def test_fr25_downloading_an_attachment_keeps_the_email_unread_in_its_folder(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-25 «Downloading an attachment keeps the email unread»
    anna, email_id = await anna_with_email(factories, reader, [CONTRACT])
    flags_before = reader.seen_flags(YANDEX, INBOX)
    assert flags_before == {1: False}

    await download_attachment(anna, email_id, 0)

    assert reader.seen_flags(YANDEX, INBOX) == flags_before


# --- FR-31 «An attachment read before sizes were kept» ---


async def test_fr31_an_attachment_stored_without_a_size_downloads_with_its_bytes(
    factories: Factories, reader: FakeMailReader, test_database_url: str
) -> None:
    # FR-31 «An attachment read before sizes were kept»: "it can be downloaded"
    anna, email_id = await anna_with_email(factories, reader, [CONTRACT])
    engine = create_engine(test_database_url)
    try:
        with engine.begin() as conn:
            conn.execute(
                text("UPDATE emails SET attachments = CAST(:old AS jsonb)"),
                {"old": '[{"name": "договор.pdf", "size": null}]'},
            )
    finally:
        engine.dispose()
    [summary] = await list_chains(anna)

    shown = (await open_chain(anna, summary["id"]))["emails"][0]["attachments"]
    response = await download_attachment_response(anna, email_id, 0)

    assert shown == [{"index": 0, "name": "договор.pdf", "size": None}]
    assert response.status_code == HTTPStatus.OK
    assert response.content == CONTRACT.content


# --- Design: which copy and which file ---


async def test_design_d2_a_different_name_at_the_index_means_the_copy_is_not_this_email(
    factories: Factories, reader: FakeMailReader
) -> None:
    # design D2: the attachment at `index` must have the stored name, else the copy is «gone»
    anna, email_id = await anna_with_email(factories, reader, [CONTRACT])
    other = Attachment("другое.pdf", content=b"other", subtype="pdf")
    replace_in_mailbox(reader, YANDEX, INBOX, 1, message_with([other], factories))

    response = await download_attachment_response(anna, email_id, 0)

    assert response.status_code == HTTPStatus.GONE
    assert response.json() == GONE
    assert b"other" not in response.content


async def test_design_d4_when_the_inbox_copy_is_gone_the_sent_copy_is_used(
    factories: Factories, reader: FakeMailReader
) -> None:
    # design D4: connected copies are tried in turn, Inbox before Sent; the first that yields wins
    anna = await factories.signed_in(await factories.confirmed_user())
    await factories.connect_mailbox(anna, YANDEX)
    raw = message_with([CONTRACT], factories)
    reader.add(YANDEX, INBOX, raw)
    reader.add(YANDEX, SENT, raw)
    await factories.read_due()
    email_id = await only_email_id(anna)
    remove_from_mailbox(reader, YANDEX, INBOX)

    response = await download_attachment_response(anna, email_id, 0)

    assert response.status_code == HTTPStatus.OK
    assert response.content == CONTRACT.content
