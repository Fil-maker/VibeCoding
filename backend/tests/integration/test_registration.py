"""FR-1, FR-2, FR-3 through the HTTP API: registration, confirmation, repeated registration."""

from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.platform.mail import FakeMailSender
from tests.factories import (
    ANNA_EMAIL,
    API,
    APP_BASE_URL,
    PASSWORD,
    Factories,
    registration_body,
    sign_in,
    token_from,
)
from tests.settable_clock import SettableClock

INVALID_LINK = "Ссылка недействительна или устарела"
NOT_CONFIRMED = "Подтвердите email: ссылка в письме, которое мы отправили"


async def test_fr1_successful_registration_sends_one_confirmation_email(
    client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-1 «Successful registration»
    response = await client.post(
        f"{API}/auth/registrations",
        json=registration_body(email="Anna@Romashka.test", password="correct-horse-1"),
    )

    assert response.status_code == 201
    assert response.json() == {"email": "anna@romashka.test", "email_sent": True}
    assert len(mail.sent) == 1
    assert mail.sent[0].to == "anna@romashka.test"
    assert mail.sent[0].subject == "Подтвердите регистрацию в VibeCoding"
    assert f"{APP_BASE_URL}/confirm-email#token=" in mail.sent[0].text


async def test_fr1_registered_administrator_is_not_confirmed_until_the_link_is_followed(
    client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-1 «Successful registration»: the administrator exists, not confirmed
    await client.post(
        f"{API}/auth/registrations", json=registration_body(email="Anna@Romashka.test")
    )

    refused = await sign_in(client, "anna@romashka.test", PASSWORD)
    confirmed = await client.post(
        f"{API}/auth/email-confirmations", json={"token": token_from(mail.sent[0])}
    )

    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "email_not_confirmed"
    assert confirmed.status_code == 200
    assert confirmed.json()["name"] == "Анна Петрова"
    assert confirmed.json()["email"] == "anna@romashka.test"
    assert confirmed.json()["role"] == "administrator"
    assert confirmed.json()["organization"]["name"] == "ООО Ромашка"


async def test_fr1_email_of_a_confirmed_user_is_refused_without_a_new_organization(
    factories: Factories, client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-1 «Email already belongs to a confirmed user»
    await factories.confirmed_admin()
    sent_before = len(mail.sent)

    response = await client.post(
        f"{API}/auth/registrations",
        json=registration_body(email=" ANNA@romashka.test ", organization_name="Другая"),
    )

    assert response.status_code == 409
    body = response.json()
    assert body["error"]["code"] == "email_taken"
    assert body["error"]["message"] == "Этот email уже зарегистрирован"
    assert len(mail.sent) == sent_before
    signed_in = await sign_in(client, ANNA_EMAIL, PASSWORD)
    assert signed_in.json()["organization"]["name"] == "ООО Ромашка"


async def test_fr1_unavailable_mail_server_is_reported_and_a_repeat_is_accepted(
    client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-1 «The mail server is unavailable»
    mail.fail_next(1)

    first = await client.post(f"{API}/auth/registrations", json=registration_body())
    second = await client.post(f"{API}/auth/registrations", json=registration_body())

    assert first.status_code == 201
    assert first.json() == {"email": ANNA_EMAIL, "email_sent": False}
    assert second.status_code == 201
    assert second.json() == {"email": ANNA_EMAIL, "email_sent": True}
    assert len(mail.sent) == 1


async def test_fr1_invalid_input_names_each_invalid_field_and_creates_nothing(
    client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-1 «Invalid input»
    response = await client.post(
        f"{API}/auth/registrations",
        json=registration_body(organization_name="", email="anna.romashka.test", password="short"),
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["fields"] == {
        "organization_name": "Укажите название организации",
        "email": "Укажите корректный email",
        "password": "Пароль должен быть от 10 до 128 символов",
    }
    assert mail.sent == []
    assert (await sign_in(client, ANNA_EMAIL, PASSWORD)).status_code == 401


@pytest.mark.parametrize(
    ("overrides", "field", "message"),
    [
        ({"name": ""}, "name", "Укажите имя"),
        ({"organization_name": "я" * 201}, "organization_name", "Укажите название организации"),
        ({"name": "я" * 201}, "name", "Укажите имя"),
        ({"password": "x" * 9}, "password", "Пароль должен быть от 10 до 128 символов"),
        ({"password": "x" * 129}, "password", "Пароль должен быть от 10 до 128 символов"),
    ],
)
async def test_fr1_values_outside_the_limits_are_refused(
    client: AsyncClient, overrides: dict[str, str], field: str, message: str
) -> None:
    # FR-1 «Invalid input»: the limits 1-200 and 10-128 characters
    response = await client.post(
        f"{API}/auth/registrations", json={**registration_body(), **overrides}
    )

    assert response.status_code == 422
    assert response.json()["error"]["fields"] == {field: message}


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "я" * 200, "organization_name": "я" * 200},
        {"password": "x" * 10},
        {"password": "x" * 128},
    ],
)
async def test_fr1_values_on_the_limits_are_accepted(
    client: AsyncClient, overrides: dict[str, str]
) -> None:
    # FR-1 «Successful registration»: the limits are inclusive
    response = await client.post(
        f"{API}/auth/registrations", json={**registration_body(), **overrides}
    )

    assert response.status_code == 201


async def test_fr2_valid_link_confirms_the_email_and_signs_in(
    client: AsyncClient, mail: FakeMailSender, clock: SettableClock
) -> None:
    # FR-2 «Confirmation by a valid link»
    await client.post(f"{API}/auth/registrations", json=registration_body())
    clock.advance(timedelta(hours=2))

    response = await client.post(
        f"{API}/auth/email-confirmations", json={"token": token_from(mail.sent[0])}
    )

    assert response.status_code == 200
    me = response.json()
    assert me["name"] == "Анна Петрова"
    assert me["role"] == "administrator"
    assert me["organization"]["name"] == "ООО Ромашка"
    assert "vc_session" in client.cookies
    assert (await client.get(f"{API}/auth/me")).status_code == 200


async def test_fr2_sign_in_before_confirmation_is_refused(
    factories: Factories, client: AsyncClient
) -> None:
    # FR-2 «Sign-in before confirmation»
    await factories.unconfirmed_admin()

    response = await sign_in(client, ANNA_EMAIL, PASSWORD)

    assert response.status_code == 403
    error = response.json()["error"]
    assert error["code"] == "email_not_confirmed"
    assert error["message"] == NOT_CONFIRMED


async def test_fr2_link_after_25_hours_changes_nothing(
    client: AsyncClient, mail: FakeMailSender, clock: SettableClock
) -> None:
    # FR-2 «Expired or used link»
    await client.post(f"{API}/auth/registrations", json=registration_body())
    clock.advance(timedelta(hours=25))

    response = await client.post(
        f"{API}/auth/email-confirmations", json={"token": token_from(mail.sent[0])}
    )

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_link"
    assert response.json()["error"]["message"] == INVALID_LINK
    assert "vc_session" not in client.cookies
    assert (await sign_in(client, ANNA_EMAIL, PASSWORD)).status_code == 403


async def test_fr2_link_used_a_second_time_is_refused(
    factories: Factories, client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-2 «Expired or used link»
    await factories.confirmed_admin()

    response = await client.post(
        f"{API}/auth/email-confirmations", json={"token": token_from(mail.sent[0])}
    )

    assert response.status_code == 400
    assert response.json()["error"]["message"] == INVALID_LINK
    assert "vc_session" not in client.cookies


async def test_fr2_unknown_token_is_refused(client: AsyncClient) -> None:
    # FR-2 «Expired or used link»
    response = await client.post(f"{API}/auth/email-confirmations", json={"token": "nonsense"})

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_link"


async def test_fr3_repeated_registration_replaces_the_unconfirmed_one(
    client: AsyncClient, mail: FakeMailSender, clock: SettableClock
) -> None:
    # FR-3 «The registrant registers again»
    await client.post(f"{API}/auth/registrations", json=registration_body())
    yesterday_token = token_from(mail.sent[0])
    clock.advance(timedelta(hours=20))

    again = await client.post(
        f"{API}/auth/registrations",
        json=registration_body(organization_name="Ромашка", password="another-horse-2"),
    )
    old_link = await client.post(f"{API}/auth/email-confirmations", json={"token": yesterday_token})
    new_link = await client.post(
        f"{API}/auth/email-confirmations", json={"token": token_from(mail.sent[1])}
    )

    assert again.status_code == 201
    assert len(mail.sent) == 2
    assert mail.sent[1].to == ANNA_EMAIL
    assert old_link.status_code == 400
    assert old_link.json()["error"]["message"] == INVALID_LINK
    assert new_link.status_code == 200
    assert new_link.json()["organization"]["name"] == "Ромашка"


async def test_fr3_repeated_registration_keeps_only_the_new_password(
    factories: Factories, client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-3 «The registrant registers again»
    await factories.unconfirmed_admin()
    await client.post(
        f"{API}/auth/registrations",
        json=registration_body(organization_name="Ромашка", password="another-horse-2"),
    )
    await client.post(f"{API}/auth/email-confirmations", json={"token": token_from(mail.sent[-1])})
    fresh = await factories.open_client()

    old = await sign_in(fresh, ANNA_EMAIL, PASSWORD)
    new = await sign_in(fresh, ANNA_EMAIL, "another-horse-2")

    assert old.status_code == 401
    assert new.status_code == 200
    assert new.json()["organization"]["name"] == "Ромашка"
