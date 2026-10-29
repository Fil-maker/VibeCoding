"""FR-22, FR-23 through the HTTP API: connecting a mailbox and keeping its password secret."""

from http import HTTPStatus
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import create_engine, text

from app.platform.mail_reader import FakeMailReader
from app.platform.secret_box import SecretBox
from tests.factories import (
    ANNA_EMAIL,
    API,
    APP_PASSWORD,
    TEST_ENCRYPTION_KEY,
    VERA_EMAIL,
    Factories,
    list_mailboxes,
)

ANNA_LOGIN = "anna@yandex.ru"
WRONG_PASSWORD_MESSAGE = "Не удалось войти в ящик: проверьте логин и пароль приложения"
OTHER_KEY = "MTExMTExMTExMTExMTExMTExMTExMTExMTExMTExMTE="
MAILBOX_KEYS = {"id", "server", "port", "login", "status", "error", "last_read_at"}


def stored_password(database_url: str, login: str) -> list[bytes | None]:
    """The `password_encrypted` column of every mailbox row with this login."""
    engine = create_engine(database_url)
    with engine.connect() as connection:
        rows = connection.execute(
            text("SELECT password_encrypted FROM mailboxes WHERE login = :login"),
            {"login": login},
        ).all()
    engine.dispose()
    return [None if row[0] is None else bytes(row[0]) for row in rows]


async def post_mailbox(client: AsyncClient, body: dict[str, Any]) -> Any:
    """POST /mailboxes with a raw body."""
    return await client.post(f"{API}/mailboxes", json=body)


async def anna_signed_in(factories: Factories) -> AsyncClient:
    """Анна, confirmed and signed in."""
    return await factories.signed_in(await factories.confirmed_user())


# --- FR-22 Connect a mailbox ---


async def test_fr22_successful_connection_shows_the_mailbox_as_pending(
    factories: Factories,
) -> None:
    # FR-22 «Successful connection»
    anna = await anna_signed_in(factories)

    response = await post_mailbox(
        anna,
        {"server": "imap.yandex.ru", "port": 993, "login": ANNA_LOGIN, "password": APP_PASSWORD},
    )

    assert response.status_code == HTTPStatus.CREATED
    body = response.json()
    assert set(body) == MAILBOX_KEYS
    assert (body["login"], body["server"], body["port"]) == (ANNA_LOGIN, "imap.yandex.ru", 993)
    assert body["status"] == "pending"
    assert body["error"] is None
    assert body["last_read_at"] is None
    assert await list_mailboxes(anna) == [body]


async def test_fr22_the_port_is_993_when_not_given(factories: Factories) -> None:
    # FR-22: the port is 993 by default
    anna = await anna_signed_in(factories)

    response = await post_mailbox(
        anna, {"server": "imap.yandex.ru", "login": ANNA_LOGIN, "password": APP_PASSWORD}
    )

    assert response.status_code == HTTPStatus.CREATED
    assert response.json()["port"] == 993


async def test_fr22_wrong_password_saves_nothing(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-22 «Wrong password»
    anna = await anna_signed_in(factories)
    reader.fail_sign_in(ANNA_LOGIN)

    response = await post_mailbox(
        anna,
        {"server": "imap.yandex.ru", "port": 993, "login": ANNA_LOGIN, "password": "wrong-pass"},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    error = response.json()["error"]
    assert error["code"] == "mailbox_sign_in_failed"
    assert error["message"] == WRONG_PASSWORD_MESSAGE
    assert await list_mailboxes(anna) == []


async def test_fr22_unreachable_server_saves_nothing(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-22 «Unreachable server»
    anna = await anna_signed_in(factories)
    reader.make_unreachable("imap.nowhere.test")

    response = await post_mailbox(
        anna,
        {"server": "imap.nowhere.test", "port": 993, "login": ANNA_LOGIN, "password": APP_PASSWORD},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    error = response.json()["error"]
    assert error["code"] == "mailbox_unreachable"
    assert error["message"] == "Не удалось подключиться к серверу imap.nowhere.test"
    assert await list_mailboxes(anna) == []


async def test_fr22_a_failed_connection_does_not_block_a_later_connect(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-22 «Unreachable server»: nothing was saved, so after the server answers it connects
    anna = await anna_signed_in(factories)
    reader.make_unreachable("imap.nowhere.test")
    await post_mailbox(
        anna,
        {"server": "imap.nowhere.test", "port": 993, "login": ANNA_LOGIN, "password": APP_PASSWORD},
    )
    reader.restore("imap.nowhere.test")

    mailbox = await factories.connect_mailbox(anna, ANNA_LOGIN, server="imap.nowhere.test")

    assert mailbox["status"] == "pending"
    assert len(await list_mailboxes(anna)) == 1


async def test_fr22_the_same_mailbox_twice_is_refused(factories: Factories) -> None:
    # FR-22 «The same mailbox twice»
    anna = await anna_signed_in(factories)
    await factories.connect_mailbox(anna, ANNA_LOGIN)

    response = await post_mailbox(
        anna,
        {"server": "imap.yandex.ru", "port": 993, "login": ANNA_LOGIN, "password": APP_PASSWORD},
    )

    assert response.status_code == HTTPStatus.CONFLICT
    error = response.json()["error"]
    assert error["code"] == "mailbox_exists"
    assert error["message"] == "Этот ящик уже подключён"
    assert len(await list_mailboxes(anna)) == 1


async def test_fr22_another_user_may_connect_the_same_login_on_the_same_server(
    factories: Factories,
) -> None:
    # FR-22: only one user may not connect the same login on the same server twice
    anna = await anna_signed_in(factories)
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))
    await factories.connect_mailbox(anna, ANNA_LOGIN)

    mailbox = await factories.connect_mailbox(vera, ANNA_LOGIN)

    assert mailbox["login"] == ANNA_LOGIN


async def test_fr22_empty_fields_are_named_one_by_one(factories: Factories) -> None:
    # FR-22 «Empty fields»
    anna = await anna_signed_in(factories)

    response = await post_mailbox(anna, {"server": "", "port": 0, "login": "", "password": ""})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["fields"] == {
        "server": "Укажите сервер IMAP",
        "port": "Порт должен быть от 1 до 65535",
        "login": "Укажите логин",
        "password": "Укажите пароль приложения",
    }
    assert await list_mailboxes(anna) == []


async def test_fr22_a_port_above_65535_is_refused(factories: Factories) -> None:
    # FR-22 «Empty fields»: the port range is 1-65535
    anna = await anna_signed_in(factories)

    response = await post_mailbox(
        anna,
        {"server": "imap.yandex.ru", "port": 65536, "login": ANNA_LOGIN, "password": APP_PASSWORD},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["error"]["fields"] == {"port": "Порт должен быть от 1 до 65535"}


async def test_fr22_mailbox_routes_need_a_signed_in_user(
    factories: Factories, client: AsyncClient
) -> None:
    # design «Interface»: every route needs a signed-in user
    await factories.confirmed_user()
    unknown = "00000000-0000-4000-8000-000000000000"

    responses = [
        await client.get(f"{API}/mailboxes"),
        await post_mailbox(client, {"server": "s", "login": "l", "password": "p"}),
        await client.post(f"{API}/mailboxes/{unknown}/refresh"),
        await client.delete(f"{API}/mailboxes/{unknown}"),
    ]

    assert [r.status_code for r in responses] == [HTTPStatus.UNAUTHORIZED] * 4
    assert {r.json()["error"]["code"] for r in responses} == {"not_signed_in"}


async def test_fr22_connecting_from_another_site_is_refused(factories: Factories) -> None:
    # design «Interface»: state-changing routes need a matching Origin
    anna = await anna_signed_in(factories)
    attacker = await factories.open_client(origin="http://attacker.test")
    attacker.cookies.set("vc_session", anna.cookies["vc_session"])

    response = await post_mailbox(
        attacker, {"server": "imap.yandex.ru", "login": ANNA_LOGIN, "password": APP_PASSWORD}
    )

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()["error"]["code"] == "forbidden_origin"
    assert await list_mailboxes(anna) == []


# --- FR-23 Keep the mailbox password secret ---


async def test_fr23_no_answer_contains_the_app_password(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-23 «The password is never shown»
    anna = await anna_signed_in(factories)
    connect = await post_mailbox(
        anna,
        {"server": "imap.yandex.ru", "port": 993, "login": ANNA_LOGIN, "password": APP_PASSWORD},
    )
    mailbox_id = connect.json()["id"]
    await factories.read_due()
    answers = [
        connect,
        await anna.get(f"{API}/mailboxes"),
        await anna.post(f"{API}/mailboxes/{mailbox_id}/refresh"),
        await anna.get(f"{API}/reply-chains"),
    ]
    reader.fail_sign_in("anna@mail.ru")
    failed = await post_mailbox(
        anna, {"server": "imap.mail.ru", "login": "anna@mail.ru", "password": APP_PASSWORD}
    )

    await factories.read_due()
    listing_answer = await anna.get(f"{API}/mailboxes")
    listing = listing_answer.json()[0]
    assert listing["login"] == ANNA_LOGIN
    assert listing["server"] == "imap.yandex.ru"
    assert listing["status"] == "read"
    assert set(listing) == MAILBOX_KEYS
    for answer in [*answers, failed, listing_answer]:
        assert APP_PASSWORD not in answer.text


async def test_fr23_the_password_is_stored_encrypted_and_deleted_on_disconnect(
    factories: Factories, test_database_url: str
) -> None:
    # FR-23: stored only in encrypted form; FR-27: disconnecting deletes the password
    anna = await anna_signed_in(factories)
    mailbox = await factories.connect_mailbox(anna, ANNA_LOGIN)

    [stored] = stored_password(test_database_url, ANNA_LOGIN)
    assert stored is not None
    assert APP_PASSWORD.encode() not in stored
    assert SecretBox(TEST_ENCRYPTION_KEY).decrypt(stored) == APP_PASSWORD
    with pytest.raises(Exception):  # noqa: B017 -- error type is not in the Interface
        SecretBox(OTHER_KEY).decrypt(stored)

    response = await anna.delete(f"{API}/mailboxes/{mailbox['id']}")

    assert response.status_code == HTTPStatus.NO_CONTENT
    assert stored_password(test_database_url, ANNA_LOGIN) == [None]


async def test_fr23_the_list_shows_the_time_of_the_last_successful_read(
    factories: Factories,
) -> None:
    # FR-23: the list shows login, server, status and the time of the last successful read
    anna = await anna_signed_in(factories)
    await factories.connect_mailbox(anna, ANNA_LOGIN)

    await factories.read_due()

    [mailbox] = await list_mailboxes(anna)
    assert mailbox["status"] == "read"
    assert mailbox["error"] is None
    assert mailbox["last_read_at"].startswith("2099-01-01T12:00")


async def test_fr23_another_user_sees_only_their_own_mailboxes(factories: Factories) -> None:
    # FR-23 «Another user's mailboxes»
    anna = await anna_signed_in(factories)
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))
    await factories.connect_mailbox(anna, ANNA_LOGIN)

    seen_by_vera = await vera.get(f"{API}/mailboxes")
    seen_by_anna = await list_mailboxes(anna)

    assert seen_by_vera.json() == []
    assert [m["login"] for m in seen_by_anna] == [ANNA_LOGIN]
    assert ANNA_LOGIN not in seen_by_vera.text
    assert ANNA_EMAIL not in seen_by_vera.text


VALID_BODY = {
    "server": "imap.yandex.ru",
    "port": 993,
    "login": ANNA_LOGIN,
    "password": APP_PASSWORD,
}


@pytest.mark.parametrize(
    ("field", "value", "message"),
    [
        ("server", "", "Укажите сервер IMAP"),
        ("login", "", "Укажите логин"),
        ("password", "", "Укажите пароль приложения"),
        ("port", 0, "Порт должен быть от 1 до 65535"),
    ],
)
async def test_fr22_one_invalid_field_is_named_alone(
    factories: Factories, field: str, value: object, message: str
) -> None:
    # FR-22 «Empty fields»: each invalid field is named, the valid ones are not
    anna = await anna_signed_in(factories)

    response = await post_mailbox(anna, {**VALID_BODY, field: value})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["fields"] == {field: message}
    assert await list_mailboxes(anna) == []
