"""FR-17, FR-20, FR-21 and the removed invitations and members routes through the HTTP API."""

from http import HTTPStatus

import pytest
from httpx import AsyncClient, Response

from app.platform.mail import FakeMailSender
from tests.factories import ANNA_EMAIL, API, Factories

UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"

# (method, path, body) of every former /invitations and /members route
REMOVED_ROUTES = [
    ("GET", "/invitations", None),
    ("POST", "/invitations", {"email": "gleb@romashka.test"}),
    ("POST", "/invitations/preview", {"token": "any-token"}),
    (
        "POST",
        "/invitations/accept",
        {"token": "any-token", "name": "Глеб", "password": "correct-horse-1"},
    ),
    ("POST", f"/invitations/{UNKNOWN_ID}/resend", None),
    ("POST", f"/invitations/{UNKNOWN_ID}/revoke", None),
    ("GET", "/members", None),
    ("POST", f"/members/{UNKNOWN_ID}/deactivate", None),
    ("POST", f"/members/{UNKNOWN_ID}/reactivate", None),
    ("PUT", f"/members/{UNKNOWN_ID}/role", {"role": "employee"}),
]


def assert_signed_out(response: Response) -> None:
    """The response is the «not signed in» error."""
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    error = response.json()["error"]
    assert error["code"] == "not_signed_in"
    assert error["message"] == "Войдите в систему"


# --- Removed invitations and members routes ---


@pytest.mark.parametrize(("method", "path", "body"), REMOVED_ROUTES)
async def test_removed_invitations_and_members_routes_answer_not_found(
    factories: Factories, method: str, path: str, body: dict[str, str] | None
) -> None:
    # design «Interface» → «Routes»: every /invitations and /members route answers 404 like
    # any unknown path
    user = await factories.signed_in(await factories.confirmed_user())

    response = await user.request(method, f"{API}{path}", json=body)
    unknown = await user.request(method, f"{API}/no-such-route", json=body)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert unknown.status_code == HTTPStatus.NOT_FOUND
    assert response.json() == unknown.json()


# --- FR-17 Protected pages and actions need a signed-in user ---


async def test_fr17_a_signed_out_request_is_refused(
    factories: Factories, client: AsyncClient
) -> None:
    # FR-17: a request without a valid session is refused as signed out
    await factories.confirmed_user()

    response = await client.get(f"{API}/auth/me")

    assert_signed_out(response)


async def test_fr17_a_forged_session_token_returns_no_data(factories: Factories) -> None:
    # FR-17 «A forged or ended session»: a token that never existed
    await factories.confirmed_user()
    forged = await factories.open_client()
    forged.cookies.set("vc_session", "forged-token-that-never-existed")

    response = await forged.get(f"{API}/auth/me")

    assert_signed_out(response)


async def test_fr17_a_session_ended_by_sign_out_returns_no_data(factories: Factories) -> None:
    # FR-17 «A forged or ended session»: a session ended by sign-out
    user = await factories.signed_in(await factories.confirmed_user())
    cookie = user.cookies["vc_session"]
    alive = await factories.open_client()
    alive.cookies.set("vc_session", cookie)
    assert (await alive.get(f"{API}/auth/me")).status_code == HTTPStatus.OK
    assert (await user.delete(f"{API}/auth/sessions/current")).status_code == HTTPStatus.NO_CONTENT
    replay = await factories.open_client()
    replay.cookies.set("vc_session", cookie)

    response = await replay.get(f"{API}/auth/me")

    assert_signed_out(response)


# --- FR-20 Actions from other sites are refused ---


async def test_fr20_a_cross_site_form_with_the_session_does_not_sign_her_out(
    factories: Factories,
) -> None:
    # FR-20 «A cross-site form»: a hidden form signing her out; her session stays
    anna = await factories.signed_in(await factories.confirmed_user())
    attacker_page = await factories.open_client(origin="http://attacker.test")
    attacker_page.cookies.set("vc_session", anna.cookies["vc_session"])

    response = await attacker_page.delete(f"{API}/auth/sessions/current")

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()["error"]["code"] == "forbidden_origin"
    assert (await anna.get(f"{API}/auth/me")).status_code == HTTPStatus.OK


# --- FR-21 Users never see each other ---


async def test_fr21_a_user_gets_only_their_own_profile(factories: Factories) -> None:
    # FR-21 «A user gets only their own profile»
    vera_account = await factories.confirmed_user(email="vera@romashka.test", name="Вера Смирнова")
    anna_account = await factories.confirmed_user()
    vera = await factories.signed_in(vera_account)
    await factories.signed_in(anna_account)

    response = await vera.get(f"{API}/auth/me")

    assert response.status_code == HTTPStatus.OK
    me = response.json()
    assert me == {
        "user_id": vera_account.user_id,
        "name": "Вера Смирнова",
        "email": "vera@romashka.test",
    }
    assert vera_account.user_id != anna_account.user_id
    assert "Анна" not in response.text
    assert ANNA_EMAIL not in response.text
    assert anna_account.user_id not in response.text


async def test_fr21_a_user_named_in_the_request_is_refused(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-21 «A user named in the request is refused»
    await factories.confirmed_user(email="vera@romashka.test", name="Вера Смирнова")
    anna_account = await factories.confirmed_user()
    client = await factories.open_client()
    sent_before = len(mail.sent)

    response = await client.post(
        f"{API}/auth/password-resets",
        json={"email": "vera@romashka.test", "user_id": anna_account.user_id},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["error"]["code"] == "validation_failed"
    assert len(mail.sent) == sent_before
