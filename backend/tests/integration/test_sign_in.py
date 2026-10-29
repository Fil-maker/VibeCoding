"""FR-4, FR-5, FR-6 through the HTTP API: sign-in, the lock, the session."""

from datetime import timedelta

from httpx import AsyncClient

from tests.factories import ANNA_EMAIL, API, PASSWORD, Factories, sign_in
from tests.settable_clock import SettableClock

INVALID_CREDENTIALS = "Неверный email или пароль"
LOCKED = "Слишком много попыток входа. Попробуйте через 15 минут"
WRONG = "wrong-horse-99"


async def fail_times(client: AsyncClient, times: int, email: str = ANNA_EMAIL) -> None:
    """Sign in with a wrong password `times` times; every attempt is refused as invalid."""
    for _ in range(times):
        response = await sign_in(client, email, WRONG)
        assert response.status_code == 401


async def test_fr4_successful_sign_in_ignores_case_and_surrounding_spaces(
    factories: Factories, client: AsyncClient
) -> None:
    # FR-4 «Successful sign-in»
    await factories.confirmed_user()

    response = await sign_in(client, " ANNA@romashka.test ", PASSWORD)

    assert response.status_code == 200
    me = response.json()
    assert me["name"] == "Анна Петрова"
    assert me["email"] == ANNA_EMAIL
    assert set(me) == {"user_id", "name", "email"}
    assert "vc_session" in client.cookies


async def test_fr4_wrong_password_and_unknown_email_give_the_same_answer(
    factories: Factories, client: AsyncClient
) -> None:
    # FR-4 «Wrong password or unknown email»
    await factories.confirmed_user()

    wrong_password = await sign_in(client, ANNA_EMAIL, WRONG)
    unknown_email = await sign_in(client, "nobody@romashka.test", PASSWORD)

    assert wrong_password.status_code == unknown_email.status_code == 401
    assert wrong_password.json() == unknown_email.json()
    error = wrong_password.json()["error"]
    assert error["code"] == "invalid_credentials"
    assert error["message"] == INVALID_CREDENTIALS
    assert "vc_session" not in client.cookies


async def test_fr4_empty_email_or_password_is_refused(client: AsyncClient) -> None:
    # FR-4 «Empty fields»
    empty_email = await sign_in(client, "", PASSWORD)
    empty_password = await sign_in(client, ANNA_EMAIL, "")

    assert empty_email.status_code == 422
    assert empty_email.json()["error"]["code"] == "validation_failed"
    assert empty_email.json()["error"]["fields"]["email"] == "Укажите email и пароль"
    assert empty_password.status_code == 422
    assert empty_password.json()["error"]["fields"]["password"] == "Укажите email и пароль"


async def test_fr4_empty_fields_are_not_counted_as_failed_attempts(
    factories: Factories, client: AsyncClient
) -> None:
    # FR-4 «Empty fields»: no failed attempt is counted
    await factories.confirmed_user()
    for _ in range(3):
        assert (await sign_in(client, ANNA_EMAIL, "")).status_code == 422
        assert (await sign_in(client, "", PASSWORD)).status_code == 422

    response = await sign_in(client, ANNA_EMAIL, PASSWORD)

    assert response.status_code == 200


async def test_fr5_fifth_wrong_password_locks_even_the_right_one(
    factories: Factories, client: AsyncClient, clock: SettableClock
) -> None:
    # FR-5 «The fifth wrong password locks sign-in»
    await factories.confirmed_user()
    for _ in range(5):
        assert (await sign_in(client, "anna@romashka.test", WRONG)).status_code == 401
        clock.advance(timedelta(minutes=2))

    response = await sign_in(client, ANNA_EMAIL, PASSWORD)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "sign_in_locked"
    assert response.json()["error"]["message"] == LOCKED
    assert "vc_session" not in client.cookies


async def test_fr4_attempts_with_other_spelling_of_the_email_count_together(
    factories: Factories, client: AsyncClient
) -> None:
    # FR-4 «A confirmed, active user SHALL sign in with their email, compared without regard to
    # case and surrounding spaces»: failures under any spelling count for one email (FR-5)
    await factories.confirmed_user()
    for email in ["anna@romashka.test", "ANNA@romashka.test", " Anna@Romashka.test ", ANNA_EMAIL]:
        await sign_in(client, email, WRONG)
    await sign_in(client, " anna@romashka.test", WRONG)

    response = await sign_in(client, ANNA_EMAIL, PASSWORD)

    assert response.status_code == 429


async def test_fr5_attempts_for_an_unknown_email_are_counted_the_same_way(
    client: AsyncClient,
) -> None:
    # FR-5 «Attempts for an unknown email SHALL be counted the same way»
    await fail_times(client, 5, "nobody@romashka.test")

    response = await sign_in(client, "nobody@romashka.test", WRONG)

    assert response.status_code == 429
    assert response.json()["error"]["code"] == "sign_in_locked"


async def test_fr5_the_lock_ends_15_minutes_after_the_fifth_failure(
    factories: Factories, client: AsyncClient, clock: SettableClock
) -> None:
    # FR-5 «The lock ends»: the lock began at the fifth failure, not at the first
    await factories.confirmed_user()
    for _ in range(5):
        await fail_times(client, 1)
        clock.advance(timedelta(minutes=2))
    clock.advance(timedelta(minutes=-2))  # the moment of the fifth failure
    assert (await sign_in(client, ANNA_EMAIL, PASSWORD)).status_code == 429
    clock.advance(timedelta(minutes=14))
    assert (await sign_in(client, ANNA_EMAIL, PASSWORD)).status_code == 429
    clock.advance(timedelta(minutes=1))

    response = await sign_in(client, ANNA_EMAIL, PASSWORD)

    assert response.status_code == 200
    assert response.json()["name"] == "Анна Петрова"


async def test_fr5_failures_spread_over_time_do_not_lock(
    factories: Factories, client: AsyncClient, clock: SettableClock
) -> None:
    # FR-5 «Failures spread over time do not lock»
    await factories.confirmed_user()
    await fail_times(client, 4)
    clock.advance(timedelta(minutes=16))
    await fail_times(client, 1)

    response = await sign_in(client, ANNA_EMAIL, PASSWORD)

    assert response.status_code == 200


async def test_fr5_a_lock_on_one_email_does_not_affect_another(
    factories: Factories, client: AsyncClient
) -> None:
    # FR-5 «Another email is not affected»
    await factories.confirmed_user()
    await factories.confirmed_user(email="boris@romashka.test", name="Борис Иванов")
    await fail_times(client, 5)
    assert (await sign_in(client, ANNA_EMAIL, PASSWORD)).status_code == 429

    response = await sign_in(client, "boris@romashka.test", PASSWORD)

    assert response.status_code == 200
    assert response.json()["name"] == "Борис Иванов"


async def test_fr5_a_successful_sign_in_clears_the_count(
    factories: Factories, client: AsyncClient
) -> None:
    # FR-5 «A successful sign-in SHALL clear the count»
    await factories.confirmed_user()
    await fail_times(client, 4)
    assert (await sign_in(client, ANNA_EMAIL, PASSWORD)).status_code == 200
    await fail_times(client, 4)

    response = await sign_in(client, ANNA_EMAIL, PASSWORD)

    assert response.status_code == 200


async def test_fr6_sign_in_sets_an_http_only_session_cookie(
    factories: Factories, client: AsyncClient
) -> None:
    # FR-6 «A session SHALL NOT be readable by the page's scripts»
    await factories.confirmed_user()

    response = await sign_in(client, ANNA_EMAIL, PASSWORD)

    cookie = next(
        value
        for value in response.headers.get_list("set-cookie")
        if value.startswith("vc_session=")
    )
    assert "httponly" in cookie.lower()


async def test_fr6_after_sign_out_the_protected_route_refuses(
    factories: Factories, client: AsyncClient
) -> None:
    # FR-6 «Sign-out»
    await factories.confirmed_user()
    await sign_in(client, ANNA_EMAIL, PASSWORD)
    old_cookie = client.cookies["vc_session"]

    signed_out = await client.delete(f"{API}/auth/sessions/current")
    after = await client.get(f"{API}/auth/me")
    replay = await factories.open_client()
    replay.cookies.set("vc_session", old_cookie)
    replayed = await replay.get(f"{API}/auth/me")

    assert signed_out.status_code == 204
    assert after.status_code == 401
    assert after.json()["error"]["code"] == "not_signed_in"
    assert replayed.status_code == 401


async def test_sign_out_without_a_session_answers_not_signed_in(client: AsyncClient) -> None:
    # Interface: DELETE /auth/sessions/current -> 401 not_signed_in when not signed in
    response = await client.delete(f"{API}/auth/sessions/current")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_signed_in"


async def test_fr6_session_expires_after_14_days(
    factories: Factories, client: AsyncClient, clock: SettableClock
) -> None:
    # FR-6 «Expired session»
    await factories.confirmed_user()
    await sign_in(client, ANNA_EMAIL, PASSWORD)
    clock.advance(timedelta(days=13))
    assert (await client.get(f"{API}/auth/me")).status_code == 200
    clock.advance(timedelta(days=2))

    response = await client.get(f"{API}/auth/me")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_signed_in"


async def test_fr6_sign_out_on_one_device_keeps_the_other(factories: Factories) -> None:
    # FR-6 «Sign-out on one device keeps the other»
    account = await factories.confirmed_user()
    laptop = await factories.signed_in(account)
    phone = await factories.signed_in(account)

    await laptop.delete(f"{API}/auth/sessions/current")

    assert (await laptop.get(f"{API}/auth/me")).status_code == 401
    assert (await phone.get(f"{API}/auth/me")).status_code == 200
