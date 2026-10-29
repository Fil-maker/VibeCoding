"""FR-24, FR-25, FR-26 through the HTTP API and `read_due_mailboxes`: reading the mailboxes."""

from datetime import timedelta
from http import HTTPStatus

from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from tests.factories import API, VERA_EMAIL, Factories, count_emails, list_mailboxes
from tests.mail_factory import INBOX, SENT, numbered_email

ANNA_LOGIN = "anna@yandex.ru"
FIVE_MINUTES = timedelta(minutes=5)


async def anna_with_mailbox(factories: Factories) -> tuple[AsyncClient, str]:
    """Анна signed in with the mailbox anna@yandex.ru connected; returns her client and its id."""
    anna = await factories.signed_in(await factories.confirmed_user())
    mailbox = await factories.connect_mailbox(anna, ANNA_LOGIN)
    return anna, mailbox["id"]


# --- FR-24 Read the mailboxes ---


async def test_fr24_first_read_takes_inbox_and_sent_of_the_last_12_months(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-24 «First read after connecting»
    now = factories.clock.now()
    anna, _ = await anna_with_mailbox(factories)
    for number in range(30):
        reader.add(ANNA_LOGIN, INBOX, numbered_email(number, now, days_ago=10 + number))
    for number in range(30, 35):
        reader.add(ANNA_LOGIN, INBOX, numbered_email(number, now, days_ago=730 + number))
    for number in range(35, 45):
        reader.add(
            ANNA_LOGIN,
            SENT,
            numbered_email(
                number, now, days_ago=10 + number, sender=ANNA_LOGIN, to=("o@stroy.test",)
            ),
        )

    read = await factories.read_due()

    assert read == 1
    assert await count_emails(anna) == 40
    [mailbox] = await list_mailboxes(anna)
    assert mailbox["status"] == "read"
    assert mailbox["last_read_at"].startswith("2099-01-01T12:00")


async def test_fr24_refresh_adds_only_the_new_email(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-24 «A new email after «Обновить»»
    now = factories.clock.now()
    anna, mailbox_id = await anna_with_mailbox(factories)
    for number in range(3):
        reader.add(ANNA_LOGIN, INBOX, numbered_email(number, now, days_ago=5))
    await factories.read_due()
    reader.add(ANNA_LOGIN, INBOX, numbered_email(3, now, days_ago=0.1))

    response = await anna.post(f"{API}/mailboxes/{mailbox_id}/refresh")
    read = await factories.read_due()

    assert response.status_code == HTTPStatus.ACCEPTED
    assert response.json()["id"] == mailbox_id
    assert read == 1
    assert await count_emails(anna) == 4


async def test_fr24_a_mailbox_that_is_not_due_is_not_read_again(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-24: the app reads every 5 minutes and on «Обновить», not more often
    now = factories.clock.now()
    anna, _ = await anna_with_mailbox(factories)
    await factories.read_due()
    reader.add(ANNA_LOGIN, INBOX, numbered_email(1, now, days_ago=0.1))
    factories.clock.advance(timedelta(minutes=4))

    read = await factories.read_due()

    assert read == 0
    assert await count_emails(anna) == 0


async def test_fr24_a_new_email_arrives_after_5_minutes_without_any_action(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-24 «A new email without any action»
    now = factories.clock.now()
    anna, _ = await anna_with_mailbox(factories)
    reader.add(ANNA_LOGIN, INBOX, numbered_email(1, now, days_ago=2))
    await factories.read_due()
    reader.add(ANNA_LOGIN, INBOX, numbered_email(2, now, days_ago=0.1))
    factories.clock.advance(FIVE_MINUTES)

    read = await factories.read_due()

    assert read == 1
    assert await count_emails(anna) == 2
    [mailbox] = await list_mailboxes(anna)
    assert mailbox["last_read_at"].startswith("2099-01-01T12:05")


async def test_fr24_refreshing_another_users_mailbox_is_not_found_and_reads_nothing(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-24 «Refreshing another user's mailbox»
    now = factories.clock.now()
    anna, mailbox_id = await anna_with_mailbox(factories)
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))
    await factories.read_due()
    reader.add(ANNA_LOGIN, INBOX, numbered_email(1, now, days_ago=0.1))

    response = await vera.post(f"{API}/mailboxes/{mailbox_id}/refresh")
    read = await factories.read_due()

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["error"]["code"] == "not_found"
    assert read == 0
    assert await count_emails(anna) == 0


# --- FR-25 Reading never changes the mailbox ---


async def test_fr25_unread_emails_stay_unread_after_a_read(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-25 «Unread emails stay unread»
    now = factories.clock.now()
    anna, _ = await anna_with_mailbox(factories)
    uids = [reader.add(ANNA_LOGIN, INBOX, numbered_email(n, now), seen=False) for n in range(3)]
    sent_uid = reader.add(ANNA_LOGIN, SENT, numbered_email(9, now, sender=ANNA_LOGIN), seen=True)

    await factories.read_due()

    assert await count_emails(anna) == 4
    assert reader.seen_flags(ANNA_LOGIN, INBOX) == dict.fromkeys(uids, False)
    assert reader.seen_flags(ANNA_LOGIN, SENT) == {sent_uid: True}


# --- FR-26 A failed read is shown and retried ---


async def test_fr26_a_revoked_password_shows_an_error_and_keeps_the_emails(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-26 «The app password was revoked»
    now = factories.clock.now()
    anna, mailbox_id = await anna_with_mailbox(factories)
    for number in range(2):
        reader.add(ANNA_LOGIN, INBOX, numbered_email(number, now))
    await factories.read_due()
    reader.fail_sign_in(ANNA_LOGIN)
    await anna.post(f"{API}/mailboxes/{mailbox_id}/refresh")

    await factories.read_due()

    [mailbox] = await list_mailboxes(anna)
    assert mailbox["status"] == "failed"
    assert (
        mailbox["error"]
        == "не удалось войти в ящик, подключите его заново с новым паролем приложения"
    )
    assert await count_emails(anna) == 2


async def test_fr26_a_server_that_is_down_is_retried_at_the_next_read(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-26 «The server is down for a while»
    now = factories.clock.now()
    anna, _ = await anna_with_mailbox(factories)
    reader.add(ANNA_LOGIN, INBOX, numbered_email(1, now))
    await factories.read_due()
    reader.make_unreachable("imap.yandex.ru")
    factories.clock.advance(FIVE_MINUTES)

    await factories.read_due()

    [failed] = await list_mailboxes(anna)
    assert failed["status"] == "failed"
    assert failed["error"] == "сервер не отвечает"

    reader.restore("imap.yandex.ru")
    reader.add(ANNA_LOGIN, INBOX, numbered_email(2, now, days_ago=0.1))
    factories.clock.advance(FIVE_MINUTES)

    read = await factories.read_due()

    [recovered] = await list_mailboxes(anna)
    assert read == 1
    assert recovered["status"] == "read"
    assert recovered["error"] is None
    assert recovered["last_read_at"].startswith("2099-01-01T12:10")
    assert await count_emails(anna) == 2


async def test_fr26_a_failed_read_is_retried_on_refresh(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-26: the app tries again on «Обновить»
    anna, mailbox_id = await anna_with_mailbox(factories)
    await factories.read_due()
    reader.make_unreachable("imap.yandex.ru")
    await anna.post(f"{API}/mailboxes/{mailbox_id}/refresh")
    await factories.read_due()
    reader.restore("imap.yandex.ru")

    await anna.post(f"{API}/mailboxes/{mailbox_id}/refresh")
    read = await factories.read_due()

    [mailbox] = await list_mailboxes(anna)
    assert read == 1
    assert mailbox["status"] == "read"


async def test_fr26_a_server_that_is_down_at_the_very_first_read_recovers_later(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-26 «The server is down for a while»: no successful read happened before
    now = factories.clock.now()
    anna, _ = await anna_with_mailbox(factories)
    reader.add(ANNA_LOGIN, INBOX, numbered_email(1, now))
    reader.make_unreachable("imap.yandex.ru")

    await factories.read_due()

    [failed] = await list_mailboxes(anna)
    assert failed["status"] == "failed"
    assert failed["error"] == "сервер не отвечает"
    assert failed["last_read_at"] is None
    assert await count_emails(anna) == 0

    reader.restore("imap.yandex.ru")
    factories.clock.advance(FIVE_MINUTES)

    read = await factories.read_due()

    [recovered] = await list_mailboxes(anna)
    assert read == 1
    assert recovered["status"] == "read"
    assert recovered["error"] is None
    assert recovered["last_read_at"].startswith("2099-01-01T12:05")
    assert await count_emails(anna) == 1
