"""Task 1.9 through the HTTP API: `error_code` of `GET /api/v1/mailboxes`, no password."""

from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.platform.mail_reader import (
    FakeMailReader,
    FolderKind,
    ImapCredentials,
    MailboxReadFailed,
)
from tests.factories import API, APP_PASSWORD, VERA_EMAIL, Factories, list_mailboxes
from tests.mail_factory import INBOX, numbered_email

ANNA_LOGIN = "anna@yandex.ru"
SERVER = "imap.yandex.ru"


async def anna_with_mailbox(factories: Factories) -> AsyncClient:
    """Анна signed in with the mailbox anna@yandex.ru connected."""
    anna = await factories.signed_in(await factories.confirmed_user())
    await factories.connect_mailbox(anna, ANNA_LOGIN)
    return anna


async def test_fr26_a_refused_sign_in_gives_error_code_sign_in_failed(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-26 «The app password was revoked» (error_code)
    anna = await anna_with_mailbox(factories)
    await factories.read_due()
    reader.fail_sign_in(ANNA_LOGIN)
    await anna.post(f"{API}/mailboxes/{(await list_mailboxes(anna))[0]['id']}/refresh")

    await factories.read_due()

    [mailbox] = await list_mailboxes(anna)
    assert mailbox["status"] == "failed"
    assert mailbox["error_code"] == "sign_in_failed"


async def test_fr26_an_unreachable_server_gives_error_code_unreachable(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-26 «The server is down for a while» (error_code)
    anna = await anna_with_mailbox(factories)
    reader.make_unreachable(SERVER)

    await factories.read_due()

    [mailbox] = await list_mailboxes(anna)
    assert mailbox["status"] == "failed"
    assert mailbox["error_code"] == "unreachable"


async def test_fr26_a_read_error_gives_error_code_read_failed(
    factories: Factories, reader: FakeMailReader, monkeypatch: pytest.MonkeyPatch
) -> None:
    # FR-26 (error_code): the server refuses to read a folder
    anna = await anna_with_mailbox(factories)

    async def refuse(
        credentials: ImapCredentials, folder: FolderKind, *args: object, **kwargs: object
    ) -> None:
        raise MailboxReadFailed("the server refused to read the folder")

    monkeypatch.setattr(reader, "fetch", refuse)

    await factories.read_due()

    [mailbox] = await list_mailboxes(anna)
    assert mailbox["status"] == "failed"
    assert mailbox["error_code"] == "read_failed"


async def test_fr26_a_pending_mailbox_has_no_error_code(factories: Factories) -> None:
    # FR-26 (error_code): null unless the status is «failed»
    anna = await anna_with_mailbox(factories)

    [mailbox] = await list_mailboxes(anna)

    assert mailbox["status"] == "pending"
    assert "error_code" in mailbox
    assert mailbox["error_code"] is None


async def test_fr26_a_read_mailbox_has_no_error_code(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-26 (error_code): null unless the status is «failed»
    anna = await anna_with_mailbox(factories)
    reader.add(ANNA_LOGIN, INBOX, numbered_email(1, factories.clock.now()))
    await factories.read_due()

    [mailbox] = await list_mailboxes(anna)

    assert mailbox["status"] == "read"
    assert "error_code" in mailbox
    assert mailbox["error_code"] is None


async def test_fr26_a_mailbox_read_again_after_a_failure_has_no_error_code(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-26 «The server is down for a while» (error_code back to null)
    anna = await anna_with_mailbox(factories)
    reader.make_unreachable(SERVER)
    await factories.read_due()
    [failed] = await list_mailboxes(anna)
    assert failed["error_code"] == "unreachable"
    reader.restore(SERVER)
    await anna.post(f"{API}/mailboxes/{failed['id']}/refresh")

    await factories.read_due()

    [recovered] = await list_mailboxes(anna)
    assert recovered["status"] == "read"
    assert recovered["error_code"] is None


async def test_fr23_no_answer_contains_the_app_password(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-23 «The password is never shown»: the connect answer and every list answer
    anna = await factories.signed_in(await factories.confirmed_user())
    connect = await anna.post(
        f"{API}/mailboxes",
        json={"server": SERVER, "port": 993, "login": ANNA_LOGIN, "password": APP_PASSWORD},
    )
    pending = await anna.get(f"{API}/mailboxes")
    reader.fail_sign_in(ANNA_LOGIN)
    await factories.read_due()
    failed = await anna.get(f"{API}/mailboxes")
    reader.make_unreachable(SERVER)
    await anna.post(f"{API}/mailboxes/{failed.json()[0]['id']}/refresh")
    await factories.read_due()
    unreachable = await anna.get(f"{API}/mailboxes")

    assert connect.status_code == HTTPStatus.CREATED
    for response in (connect, pending, failed, unreachable):
        assert APP_PASSWORD not in response.text
        assert "password" not in response.text


async def test_fr23_another_users_list_holds_none_of_annas_mailboxes(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-23 «Another user's mailboxes»
    anna = await anna_with_mailbox(factories)
    reader.fail_sign_in(ANNA_LOGIN)
    await factories.read_due()
    [annas] = await list_mailboxes(anna)
    assert annas["error_code"] == "sign_in_failed"
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))

    response = await vera.get(f"{API}/mailboxes")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == []
    assert ANNA_LOGIN not in response.text
