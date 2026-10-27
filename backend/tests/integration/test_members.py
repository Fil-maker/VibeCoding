"""FR-13, FR-14 through the HTTP API: the members list, deactivate and reactivate."""

from http import HTTPStatus

import pytest
from httpx import AsyncClient

from tests.factories import ANNA_EMAIL, API, PASSWORD, Factories, sign_in
from tests.members_api import (
    ACCOUNT_DISABLED,
    BORIS_EMAIL,
    CANNOT_DEACTIVATE_SELF,
    DINA_EMAIL,
    NOT_FOUND,
    UNKNOWN_ID,
    VERA_EMAIL,
    assert_error,
    deactivate,
    list_members,
    member_of,
    reactivate,
    romashka_team,
    two_administrators,
)


async def test_fr13_the_list_shows_the_three_members_by_name_without_other_organizations(
    factories: Factories,
) -> None:
    # FR-13 «The members list»
    anna = await factories.confirmed_admin()
    anna_client = await factories.signed_in(anna)
    dina = await factories.employee(anna_client, email=DINA_EMAIL, name="Дина Орлова")
    boris = await factories.employee(anna_client, email=BORIS_EMAIL)
    vera = await factories.signed_in(
        await factories.confirmed_admin(email=VERA_EMAIL, organization_name="Лютик", name="Вера")
    )
    await factories.employee(vera, email="arkadiy@lyutik.test", name="Аркадий Лютиков")

    response = await anna_client.get(f"{API}/members")

    assert response.status_code == HTTPStatus.OK
    page = response.json()
    assert page["next_cursor"] is None
    assert page["items"] == [
        {
            "id": anna.user_id,
            "name": "Анна Петрова",
            "email": ANNA_EMAIL,
            "role": "administrator",
            "is_active": True,
        },
        {
            "id": boris.user_id,
            "name": "Борис Иванов",
            "email": BORIS_EMAIL,
            "role": "employee",
            "is_active": True,
        },
        {
            "id": dina.user_id,
            "name": "Дина Орлова",
            "email": DINA_EMAIL,
            "role": "employee",
            "is_active": True,
        },
    ]
    assert [m["name"] for m in await list_members(vera)] == ["Аркадий Лютиков", "Вера"]


async def test_fr13_the_list_is_paged_by_name_with_limit_and_cursor(factories: Factories) -> None:
    # FR-13 «ordered by name»; Interface: Page[Member] with limit and cursor
    admin = await factories.signed_in(await factories.confirmed_admin())
    await factories.employee(admin, email=DINA_EMAIL, name="Дина Орлова")
    await factories.employee(admin, email=BORIS_EMAIL)

    first = (await admin.get(f"{API}/members", params={"limit": 2})).json()
    second = (
        await admin.get(f"{API}/members", params={"limit": 2, "cursor": first["next_cursor"]})
    ).json()

    assert [m["name"] for m in first["items"]] == ["Анна Петрова", "Борис Иванов"]
    assert first["next_cursor"] is not None
    assert [m["name"] for m in second["items"]] == ["Дина Орлова"]
    assert second["next_cursor"] is None


@pytest.mark.parametrize("limit", ["0", "101", "-1", "abc"])
async def test_fr13_a_bad_limit_is_a_validation_error_on_the_limit(
    factories: Factories, limit: str
) -> None:
    # Interface: Page query limit 1-100; 422 validation_failed names the field
    admin = await factories.signed_in(await factories.confirmed_admin())

    response = await admin.get(f"{API}/members", params={"limit": limit})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert "limit" in error["fields"]


@pytest.mark.parametrize("limit", ["1", "100"])
async def test_fr13_limits_on_the_bounds_are_accepted(factories: Factories, limit: str) -> None:
    # Interface: Page query limit 1-100
    admin = await factories.signed_in(await factories.confirmed_admin())

    response = await admin.get(f"{API}/members", params={"limit": limit})

    assert response.status_code == HTTPStatus.OK
    assert [m["name"] for m in response.json()["items"]] == ["Анна Петрова"]


async def test_fr13_unconfirmed_registrants_and_pending_invitees_are_not_members(
    factories: Factories,
) -> None:
    # FR-13 clause «the confirmed members of their organization»
    admin = await factories.signed_in(await factories.confirmed_admin())
    invited = await admin.post(f"{API}/invitations", json={"email": DINA_EMAIL})
    assert invited.status_code == HTTPStatus.CREATED
    await factories.unconfirmed_admin(
        email="pavel@pavel.test", name="Павел", organization_name="Павел и Ко"
    )

    members = await list_members(admin)

    assert [m["email"] for m in members] == [ANNA_EMAIL]
    pavel = await factories.open_client()
    assert (await sign_in(pavel, "pavel@pavel.test", PASSWORD)).status_code == HTTPStatus.FORBIDDEN


async def test_fr13_a_garbage_cursor_is_refused(factories: Factories) -> None:
    # Interface: invalid_cursor (400, any paged list)
    admin = await factories.signed_in(await factories.confirmed_admin())

    response = await admin.get(f"{API}/members", params={"cursor": "garbage"})

    assert_error(response, 400, "invalid_cursor", "Некорректный курсор страницы")


async def test_fr14_deactivating_an_employee_ends_his_sessions_and_refuses_sign_in(
    factories: Factories,
) -> None:
    # FR-14 «Deactivating an employee»
    anna, _, boris_client, boris = await romashka_team(factories)
    second_session = await factories.signed_in(boris)

    response = await deactivate(anna, boris.user_id)

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "id": boris.user_id,
        "name": "Борис Иванов",
        "email": BORIS_EMAIL,
        "role": "employee",
        "is_active": False,
    }
    for session in (boris_client, second_session):
        assert (await session.get(f"{API}/auth/me")).status_code == HTTPStatus.UNAUTHORIZED
    refused = await sign_in(await factories.open_client(), BORIS_EMAIL, PASSWORD)
    assert_error(refused, 403, "account_disabled", ACCOUNT_DISABLED)
    kept = await member_of(anna, boris.user_id)
    assert (kept["name"], kept["role"], kept["is_active"]) == ("Борис Иванов", "employee", False)


async def test_fr14_the_session_cookie_kept_before_the_deactivation_is_dead(
    factories: Factories, client: AsyncClient
) -> None:
    # FR-14 «their sessions SHALL end at once»: a copied cookie is refused as signed out
    anna, _, boris_client, boris = await romashka_team(factories)
    client.cookies.set("vc_session", boris_client.cookies["vc_session"])
    assert (await client.get(f"{API}/auth/me")).status_code == HTTPStatus.OK
    await deactivate(anna, boris.user_id)

    response = await client.get(f"{API}/auth/me")

    assert_error(response, 401, "not_signed_in", "Войдите в систему")


async def test_fr14_reactivating_lets_the_member_sign_in_with_the_old_password(
    factories: Factories,
) -> None:
    # FR-14 «Reactivating»
    anna, _, _, boris = await romashka_team(factories)
    await deactivate(anna, boris.user_id)

    response = await reactivate(anna, boris.user_id)

    assert response.status_code == HTTPStatus.OK
    assert response.json()["is_active"] is True
    signed = await sign_in(await factories.open_client(), BORIS_EMAIL, PASSWORD)
    assert signed.status_code == HTTPStatus.OK
    assert signed.json()["role"] == "employee"
    assert (await member_of(anna, boris.user_id))["is_active"] is True


async def test_fr14_the_only_administrator_cannot_deactivate_himself(
    factories: Factories,
) -> None:
    # FR-14 «Deactivating oneself»: Анна is the only administrator; cannot_deactivate_self wins
    anna_account = await factories.confirmed_admin()
    anna = await factories.signed_in(anna_account)

    response = await deactivate(anna, anna_account.user_id)

    assert_error(response, 409, "cannot_deactivate_self", CANNOT_DEACTIVATE_SELF)
    assert (await member_of(anna, anna_account.user_id))["is_active"] is True
    assert (await anna.get(f"{API}/auth/me")).status_code == HTTPStatus.OK


async def test_fr14_an_administrator_cannot_deactivate_himself_with_another_one_active(
    factories: Factories,
) -> None:
    # FR-14 «Deactivating oneself»: the same refusal when a second administrator exists
    anna, anna_account, _, _ = await two_administrators(factories)

    response = await deactivate(anna, anna_account.user_id)

    assert_error(response, 409, "cannot_deactivate_self", CANNOT_DEACTIVATE_SELF)
    assert (await member_of(anna, anna_account.user_id))["is_active"] is True
    assert (await anna.get(f"{API}/auth/me")).status_code == HTTPStatus.OK


async def test_fr14_an_administrator_can_deactivate_another_administrator(
    factories: Factories,
) -> None:
    # FR-14: another member of the organization, while an active administrator remains
    anna, _, boris_client, boris = await two_administrators(factories)

    response = await deactivate(anna, boris.user_id)

    assert response.status_code == HTTPStatus.OK
    assert response.json()["is_active"] is False
    assert (await boris_client.get(f"{API}/auth/me")).status_code == HTTPStatus.UNAUTHORIZED


async def test_fr14_deactivating_an_unknown_member_is_not_found(factories: Factories) -> None:
    # Interface: deactivate answers 404 for an unknown id
    admin = await factories.signed_in(await factories.confirmed_admin())

    response = await deactivate(admin, UNKNOWN_ID)

    assert_error(response, 404, "not_found", NOT_FOUND)


async def test_fr14_reactivating_an_unknown_member_is_not_found(factories: Factories) -> None:
    # Interface: reactivate answers 404 for an unknown id
    admin = await factories.signed_in(await factories.confirmed_admin())

    response = await reactivate(admin, UNKNOWN_ID)

    assert_error(response, 404, "not_found", NOT_FOUND)
