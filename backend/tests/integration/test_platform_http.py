"""The error shape, the 422 handler and the Origin check, seen through the slice routes."""

import pytest
from httpx import AsyncClient

from app.platform.mail import FakeMailSender
from tests.factories import ANNA_EMAIL, API, APP_BASE_URL, Factories, registration_body

FORBIDDEN_ORIGIN = "Запрос отклонён"


async def test_error_has_the_code_and_message_shape(client: AsyncClient) -> None:
    response = await client.get(f"{API}/auth/me")

    assert response.status_code == 401
    assert response.json() == {"error": {"code": "not_signed_in", "message": "Войдите в систему"}}


async def test_validation_error_is_validation_failed_with_russian_field_messages(
    client: AsyncClient,
) -> None:
    response = await client.post(
        f"{API}/auth/registrations",
        json=registration_body(name="", email="no-at-sign", password="short"),
    )

    assert response.status_code == 422
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["message"] == "Проверьте поля формы"
    assert error["fields"] == {
        "name": "Укажите имя",
        "email": "Укажите корректный email",
        "password": "Пароль должен быть от 10 до 128 символов",
    }


async def test_a_missing_field_is_named_in_the_validation_error(client: AsyncClient) -> None:
    body = registration_body()
    del body["password"]

    response = await client.post(f"{API}/auth/registrations", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert "password" in response.json()["error"]["fields"]


async def test_origin_request_without_origin_is_refused(factories: Factories) -> None:
    # Interface: every state-changing route also answers 403 forbidden_origin: a missing Origin
    no_origin = await factories.open_client(origin=None)

    response = await no_origin.post(
        f"{API}/auth/sessions", json={"email": ANNA_EMAIL, "password": "whatever-horse"}
    )

    assert response.status_code == 403
    assert response.json() == {"error": {"code": "forbidden_origin", "message": FORBIDDEN_ORIGIN}}


@pytest.mark.parametrize(
    "origin",
    [
        "http://evil.test",
        "http://localhost:5174",
        "https://localhost:5173",
        "http://localhost:5173.evil.test",
    ],
)
async def test_origin_request_with_a_foreign_origin_is_refused(
    factories: Factories, origin: str
) -> None:
    # Interface: every state-changing route also answers 403 forbidden_origin: a foreign Origin
    foreign = await factories.open_client(origin=origin)

    response = await foreign.post(
        f"{API}/auth/sessions", json={"email": ANNA_EMAIL, "password": "whatever-horse"}
    )

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_origin"
    assert response.json()["error"]["message"] == FORBIDDEN_ORIGIN


async def test_origin_request_with_the_matching_origin_passes(client: AsyncClient) -> None:
    # Interface: a matching Origin passes
    response = await client.post(
        f"{API}/auth/sessions",
        json={"email": ANNA_EMAIL, "password": "whatever-horse"},
        headers={"Origin": APP_BASE_URL},
    )

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "invalid_credentials"


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("POST", "/auth/registrations", registration_body()),
        ("POST", "/auth/email-confirmations", {"token": "x"}),
        ("POST", "/auth/sessions", {"email": ANNA_EMAIL, "password": "x"}),
        ("DELETE", "/auth/sessions/current", None),
        ("POST", "/auth/password-resets", {"email": ANNA_EMAIL}),
        ("POST", "/auth/password-resets/complete", {"token": "x", "password": "y" * 10}),
        ("POST", "/invitations", {"email": "boris@romashka.test"}),
        ("POST", "/invitations/00000000-0000-0000-0000-000000000001/resend", None),
        ("POST", "/invitations/00000000-0000-0000-0000-000000000001/revoke", None),
        ("POST", "/invitations/accept", {"token": "x", "name": "Борис", "password": "y" * 10}),
        ("POST", "/invitations/preview", {"token": "x"}),
        ("POST", "/members/00000000-0000-0000-0000-000000000001/deactivate", None),
        ("POST", "/members/00000000-0000-0000-0000-000000000001/reactivate", None),
        ("PUT", "/members/00000000-0000-0000-0000-000000000001/role", {"role": "employee"}),
    ],
)
async def test_origin_every_state_changing_auth_route_checks_the_origin(
    factories: Factories, method: str, path: str, body: dict[str, str] | None
) -> None:
    # Interface: every state-changing route also answers 403 forbidden_origin
    foreign = await factories.open_client(origin="http://evil.test")

    response = await foreign.request(method, f"{API}{path}", json=body)

    assert response.status_code == 403
    assert response.json()["error"]["code"] == "forbidden_origin"


async def test_origin_refused_registration_creates_nothing(
    factories: Factories, client: AsyncClient, mail: FakeMailSender
) -> None:
    # Interface: every state-changing route also answers 403 forbidden_origin
    foreign = await factories.open_client(origin="http://evil.test")

    refused = await foreign.post(f"{API}/auth/registrations", json=registration_body())
    accepted = await client.post(f"{API}/auth/registrations", json=registration_body())

    assert refused.status_code == 403
    assert accepted.status_code == 201
    assert len(mail.sent) == 1


async def test_origin_foreign_request_with_a_session_cookie_is_refused_and_the_session_stays(
    factories: Factories,
) -> None:
    # FR-20 «even if the browser sends the user's session along»
    account = await factories.confirmed_admin()
    signed_in = await factories.signed_in(account)
    cookie = signed_in.cookies["vc_session"]
    foreign = await factories.open_client(origin="http://evil.test")
    foreign.cookies.set("vc_session", cookie)

    refused = await foreign.delete(f"{API}/auth/sessions/current")

    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "forbidden_origin"
    assert (await signed_in.get(f"{API}/auth/me")).status_code == 200


async def test_a_read_route_needs_no_origin(factories: Factories) -> None:
    # Interface: only state-changing requests need an Origin
    no_origin = await factories.open_client(origin=None)

    response = await no_origin.get(f"{API}/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_signed_in"
