"""FR-27 through the HTTP API and `read_due_mailboxes`: disconnecting and reconnecting."""

from datetime import timedelta
from http import HTTPStatus

from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from tests.factories import API, VERA_EMAIL, Factories, count_emails, list_mailboxes
from tests.mail_factory import INBOX, numbered_email

ANNA_LOGIN = "anna@yandex.ru"


async def anna_with_mailbox(factories: Factories) -> tuple[AsyncClient, str]:
    """Анна signed in with the mailbox anna@yandex.ru connected; returns her client and its id."""
    anna = await factories.signed_in(await factories.confirmed_user())
    mailbox = await factories.connect_mailbox(anna, ANNA_LOGIN)
    return anna, mailbox["id"]


async def test_fr27_disconnecting_keeps_the_emails_and_stops_reading(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-27 «Disconnecting keeps the emails»
    now = factories.clock.now()
    anna, mailbox_id = await anna_with_mailbox(factories)
    for number in range(2):
        reader.add(ANNA_LOGIN, INBOX, numbered_email(number, now))
    await factories.read_due()

    response = await anna.delete(f"{API}/mailboxes/{mailbox_id}")
    reader.add(ANNA_LOGIN, INBOX, numbered_email(5, now, days_ago=0.1))
    factories.clock.advance(timedelta(minutes=30))
    read = await factories.read_due()

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert await list_mailboxes(anna) == []
    assert read == 0
    assert await count_emails(anna) == 2


async def test_fr27_a_disconnected_mailbox_answers_not_found_to_refresh_and_delete(
    factories: Factories,
) -> None:
    # design «Interface»: a disconnected mailbox answers 404 to refresh and delete
    anna, mailbox_id = await anna_with_mailbox(factories)
    await anna.delete(f"{API}/mailboxes/{mailbox_id}")

    refresh = await anna.post(f"{API}/mailboxes/{mailbox_id}/refresh")
    delete = await anna.delete(f"{API}/mailboxes/{mailbox_id}")

    assert refresh.status_code == delete.status_code == HTTPStatus.NOT_FOUND
    assert refresh.json()["error"]["code"] == "not_found"


async def test_fr27_connecting_again_adds_the_new_emails_without_duplicates(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-27 «Connecting again»
    now = factories.clock.now()
    anna, mailbox_id = await anna_with_mailbox(factories)
    for number in range(2):
        reader.add(ANNA_LOGIN, INBOX, numbered_email(number, now, days_ago=3))
    await factories.read_due()
    await anna.delete(f"{API}/mailboxes/{mailbox_id}")
    factories.clock.advance(timedelta(days=1))
    reader.add(ANNA_LOGIN, INBOX, numbered_email(7, now, days_ago=0.5))

    await factories.connect_mailbox(anna, ANNA_LOGIN)
    read = await factories.read_due()

    [mailbox] = await list_mailboxes(anna)
    assert read == 1
    assert mailbox["status"] == "read"
    assert await count_emails(anna) == 3


async def test_fr27_disconnecting_another_users_mailbox_is_not_found(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-27 «Disconnecting another user's mailbox»
    anna, mailbox_id = await anna_with_mailbox(factories)
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))
    now = factories.clock.now()
    reader.add(ANNA_LOGIN, INBOX, numbered_email(1, now, days_ago=2))
    await factories.read_due()

    response = await vera.delete(f"{API}/mailboxes/{mailbox_id}")
    reader.add(ANNA_LOGIN, INBOX, numbered_email(2, now, days_ago=0.1))
    factories.clock.advance(timedelta(minutes=5))
    read_after = await factories.read_due()

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["error"]["code"] == "not_found"
    [mailbox] = await list_mailboxes(anna)
    assert mailbox["id"] == mailbox_id
    assert mailbox["status"] == "read"
    assert read_after == 1
    assert await count_emails(anna) == 2
