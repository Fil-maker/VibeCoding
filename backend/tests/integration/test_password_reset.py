"""FR-7, FR-8 through the HTTP API: the password reset."""

from datetime import timedelta

from httpx import AsyncClient, Response

from app.platform.mail import FakeMailSender
from tests.factories import ANNA_EMAIL, API, APP_BASE_URL, PASSWORD, Factories, sign_in, token_from
from tests.settable_clock import SettableClock

INVALID_LINK = "Ссылка недействительна или устарела"
NEW_PASSWORD = "new-correct-horse-2"
TOO_SHORT = "Пароль должен быть от 10 до 128 символов"


async def request_reset(client: AsyncClient, email: str = ANNA_EMAIL) -> int:
    """POST /auth/password-resets; the status code."""
    return (await client.post(f"{API}/auth/password-resets", json={"email": email})).status_code


async def complete_reset(client: AsyncClient, token: str, password: str = NEW_PASSWORD) -> Response:
    """POST /auth/password-resets/complete."""
    return await client.post(
        f"{API}/auth/password-resets/complete", json={"token": token, "password": password}
    )


async def test_fr7_reset_for_a_registered_email_sends_one_email(
    factories: Factories, client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-7 «Reset requested for a registered email»
    await factories.confirmed_admin()
    sent_before = len(mail.sent)

    response = await client.post(f"{API}/auth/password-resets", json={"email": ANNA_EMAIL})

    assert response.status_code == 202
    assert len(mail.sent) == sent_before + 1
    assert mail.sent[-1].to == ANNA_EMAIL
    assert mail.sent[-1].subject == "Сброс пароля в VibeCoding"
    assert f"{APP_BASE_URL}/reset-password#token=" in mail.sent[-1].text


async def test_fr7_reset_for_an_unknown_email_sends_nothing_and_answers_the_same(
    factories: Factories, client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-7 «Reset requested for an unknown email»
    await factories.confirmed_admin()
    known = await client.post(f"{API}/auth/password-resets", json={"email": ANNA_EMAIL})
    sent_after_known = len(mail.sent)

    unknown = await client.post(
        f"{API}/auth/password-resets", json={"email": "nobody@romashka.test"}
    )

    assert unknown.status_code == known.status_code == 202
    assert unknown.content == known.content
    assert len(mail.sent) == sent_after_known


async def test_fr7_reset_for_an_unconfirmed_registrant_sends_nothing(
    factories: Factories, client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-7: the link goes only to a confirmed user
    await factories.unconfirmed_admin()
    sent_before = len(mail.sent)

    status = await request_reset(client)

    assert status == 202
    assert len(mail.sent) == sent_before


async def test_fr7_a_new_request_replaces_the_earlier_link(
    factories: Factories, client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-7 «A new request replaces the earlier link»
    await factories.confirmed_admin()
    await request_reset(client)
    first_token = token_from(mail.sent[-1])
    await request_reset(client)
    second_token = token_from(mail.sent[-1])

    first = await complete_reset(client, first_token)
    second = await complete_reset(client, second_token)

    assert first.status_code == 400
    assert first.json()["error"]["code"] == "invalid_link"
    assert first.json()["error"]["message"] == INVALID_LINK
    assert second.status_code == 204


async def test_fr7_invalid_email_is_a_validation_error(
    client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-7: the email is entered
    response = await client.post(f"{API}/auth/password-resets", json={"email": "not-an-email"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert response.json()["error"]["fields"]["email"] == "Укажите корректный email"
    assert mail.sent == []


async def test_fr8_reset_ends_old_sessions_and_switches_to_the_new_password(
    factories: Factories, client: AsyncClient, mail: FakeMailSender, clock: SettableClock
) -> None:
    # FR-8 «Password reset ends old sessions»
    account = await factories.confirmed_admin()
    phone = await factories.signed_in(account)
    await request_reset(client)
    clock.advance(timedelta(minutes=30))

    response = await complete_reset(client, token_from(mail.sent[-1]))

    assert response.status_code == 204
    assert (await phone.get(f"{API}/auth/me")).status_code == 401
    assert (await sign_in(client, ANNA_EMAIL, PASSWORD)).status_code == 401
    assert (await sign_in(client, ANNA_EMAIL, NEW_PASSWORD)).status_code == 200


async def test_fr8_reset_after_61_minutes_changes_nothing(
    factories: Factories, client: AsyncClient, mail: FakeMailSender, clock: SettableClock
) -> None:
    # FR-8 «Expired or used reset link»
    await factories.confirmed_admin()
    await request_reset(client)
    clock.advance(timedelta(minutes=61))

    response = await complete_reset(client, token_from(mail.sent[-1]))

    assert response.status_code == 400
    assert response.json()["error"]["code"] == "invalid_link"
    assert response.json()["error"]["message"] == INVALID_LINK
    assert (await sign_in(client, ANNA_EMAIL, PASSWORD)).status_code == 200
    assert (await sign_in(client, ANNA_EMAIL, NEW_PASSWORD)).status_code == 401


async def test_fr8_reset_link_used_a_second_time_changes_nothing(
    factories: Factories, client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-8 «Expired or used reset link»
    await factories.confirmed_admin()
    await request_reset(client)
    token = token_from(mail.sent[-1])
    assert (await complete_reset(client, token)).status_code == 204

    second = await complete_reset(client, token, "third-correct-horse-3")

    assert second.status_code == 400
    assert second.json()["error"]["message"] == INVALID_LINK
    assert (await sign_in(client, ANNA_EMAIL, NEW_PASSWORD)).status_code == 200
    assert (await sign_in(client, ANNA_EMAIL, "third-correct-horse-3")).status_code == 401


async def test_fr8_too_short_password_keeps_the_password_and_the_link(
    factories: Factories, client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-8 «Too short new password»
    await factories.confirmed_admin()
    await request_reset(client)
    token = token_from(mail.sent[-1])

    short = await complete_reset(client, token, "short")
    long = await complete_reset(client, token, "x" * 129)

    assert short.status_code == 422
    assert short.json()["error"]["code"] == "validation_failed"
    assert short.json()["error"]["fields"] == {"password": TOO_SHORT}
    assert long.status_code == 422
    assert (await sign_in(client, ANNA_EMAIL, PASSWORD)).status_code == 200
    assert (await complete_reset(client, token)).status_code == 204


async def test_fr8_completed_reset_clears_the_sign_in_lock(
    factories: Factories, client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-5 «A completed password reset SHALL clear the count», FR-8
    await factories.confirmed_admin()
    for _ in range(5):
        await sign_in(client, ANNA_EMAIL, "wrong-horse-99")
    assert (await sign_in(client, ANNA_EMAIL, PASSWORD)).status_code == 429
    await request_reset(client)

    await complete_reset(client, token_from(mail.sent[-1]))

    assert (await sign_in(client, ANNA_EMAIL, NEW_PASSWORD)).status_code == 200


async def test_fr7_reset_for_a_deactivated_user_still_sends_the_link(
    factories: Factories, client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-7 «For a confirmed user, active or not»
    admin = await factories.signed_in(await factories.confirmed_admin())
    boris = await factories.employee(admin, active=False)
    sent_before = len(mail.sent)

    response = await client.post(f"{API}/auth/password-resets", json={"email": boris.email})

    assert response.status_code == 202
    assert len(mail.sent) == sent_before + 1
    assert mail.sent[-1].to == boris.email
    assert mail.sent[-1].subject == "Сброс пароля в VibeCoding"
    assert f"{APP_BASE_URL}/reset-password#token=" in mail.sent[-1].text


async def test_fr8_a_deactivated_user_sets_a_new_password_but_is_still_refused_sign_in(
    factories: Factories, client: AsyncClient, mail: FakeMailSender
) -> None:
    # FR-8: a deactivated user can set a new password, sign-in stays refused (FR-14)
    admin = await factories.signed_in(await factories.confirmed_admin())
    boris = await factories.employee(admin, active=False)
    await request_reset(client, boris.email)

    completed = await complete_reset(client, token_from(mail.sent[-1]))

    assert completed.status_code == 204
    refused = await sign_in(client, boris.email, NEW_PASSWORD)
    assert refused.status_code == 403
    assert refused.json()["error"]["code"] == "account_disabled"
    assert (
        refused.json()["error"]["message"]
        == "Учётная запись отключена. Обратитесь к администратору организации"
    )
    reactivated = await admin.post(f"{API}/members/{boris.user_id}/reactivate")
    assert reactivated.status_code == 200
    assert (await sign_in(client, boris.email, NEW_PASSWORD)).status_code == 200
