"""FR-15, FR-16 through the HTTP API: roles, the last administrator, concurrent changes."""

import asyncio
from http import HTTPStatus

import pytest

from tests.factories import API, Factories
from tests.members_api import (
    BORIS_EMAIL,
    LAST_ADMINISTRATOR,
    MEMBER_INACTIVE,
    NOT_FOUND,
    UNKNOWN_ID,
    assert_error,
    deactivate,
    list_members,
    member_of,
    romashka_team,
    set_role,
    two_administrators,
)


async def test_fr15_appointing_an_administrator_applies_to_his_next_request(
    factories: Factories,
) -> None:
    # FR-15 «Appointing an administrator»
    anna, _, boris_client, boris = await romashka_team(factories)
    assert (await boris_client.get(f"{API}/members")).status_code == HTTPStatus.NOT_FOUND

    response = await set_role(anna, boris.user_id, "administrator")

    assert response.status_code == HTTPStatus.OK
    assert response.json() == {
        "id": boris.user_id,
        "name": "Борис Иванов",
        "email": BORIS_EMAIL,
        "role": "administrator",
        "is_active": True,
    }
    members = await boris_client.get(f"{API}/members")
    assert members.status_code == HTTPStatus.OK
    assert len(members.json()["items"]) == 2
    invited = await boris_client.post(f"{API}/invitations", json={"email": "dina@romashka.test"})
    assert invited.status_code == HTTPStatus.CREATED
    assert (await boris_client.get(f"{API}/auth/me")).json()["role"] == "administrator"


async def test_fr15_removing_the_role_applies_to_the_next_request_without_a_new_sign_in(
    factories: Factories,
) -> None:
    # FR-15 «Removing the role»
    anna, anna_account, boris_client, _ = await two_administrators(factories)

    response = await set_role(boris_client, anna_account.user_id, "employee")

    assert response.status_code == HTTPStatus.OK
    assert response.json()["role"] == "employee"
    assert_error(await anna.get(f"{API}/members"), 404, "not_found", NOT_FOUND)
    me = await anna.get(f"{API}/auth/me")
    assert me.status_code == HTTPStatus.OK
    assert me.json()["role"] == "employee"
    assert (await member_of(boris_client, anna_account.user_id))["role"] == "employee"


async def test_fr15_the_role_of_an_inactive_member_cannot_be_changed_to_administrator(
    factories: Factories,
) -> None:
    # FR-15 «an active employee»; Interface: 409 member_inactive
    anna, _, _, boris = await romashka_team(factories)
    await deactivate(anna, boris.user_id)

    response = await set_role(anna, boris.user_id, "administrator")

    assert_error(response, 409, "member_inactive", MEMBER_INACTIVE)
    assert (await member_of(anna, boris.user_id))["role"] == "employee"


async def test_fr15_an_unknown_member_is_not_found(factories: Factories) -> None:
    # Interface: PUT /members/{id}/role answers 404 for an unknown id
    admin = await factories.signed_in(await factories.confirmed_admin())

    response = await set_role(admin, UNKNOWN_ID, "employee")

    assert_error(response, 404, "not_found", NOT_FOUND)


async def test_fr15_an_unknown_role_is_a_validation_error(factories: Factories) -> None:
    # Interface: role is "administrator" or "employee"
    anna, _, _, boris = await romashka_team(factories)

    response = await set_role(anna, boris.user_id, "owner")

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["error"]["code"] == "validation_failed"
    assert (await member_of(anna, boris.user_id))["role"] == "employee"


async def test_fr16_the_last_administrator_cannot_make_himself_an_employee(
    factories: Factories,
) -> None:
    # FR-16 «The last administrator removes their own role»
    anna, anna_account, _, _ = await romashka_team(factories)

    response = await set_role(anna, anna_account.user_id, "employee")

    assert_error(response, 409, "last_administrator", LAST_ADMINISTRATOR)
    assert (await member_of(anna, anna_account.user_id))["role"] == "administrator"
    assert (await anna.get(f"{API}/members")).status_code == HTTPStatus.OK


async def test_fr16_an_inactive_administrator_does_not_count_as_the_remaining_one(
    factories: Factories,
) -> None:
    # FR-16 «at least one active administrator»
    anna, anna_account, _, boris = await two_administrators(factories)
    assert (await deactivate(anna, boris.user_id)).status_code == HTTPStatus.OK

    response = await set_role(anna, anna_account.user_id, "employee")

    assert_error(response, 409, "last_administrator", LAST_ADMINISTRATOR)
    assert (await member_of(anna, anna_account.user_id))["role"] == "administrator"


async def test_fr16_an_administrator_may_step_down_while_another_one_is_active(
    factories: Factories,
) -> None:
    # FR-16: the rule is at least one, not exactly one
    anna, anna_account, boris_client, _ = await two_administrators(factories)

    response = await set_role(anna, anna_account.user_id, "employee")

    assert response.status_code == HTTPStatus.OK
    assert (await member_of(boris_client, anna_account.user_id))["role"] == "employee"


@pytest.mark.parametrize("attempt", range(5))
async def test_fr16_two_administrators_demoting_each_other_at_once_leave_one(
    factories: Factories, attempt: int
) -> None:
    # FR-16 «Two administrators remove each other at once»
    anna, anna_account, boris_client, boris = await two_administrators(factories)

    to_boris, to_anna = await asyncio.gather(
        set_role(anna, boris.user_id, "employee"),
        set_role(boris_client, anna_account.user_id, "employee"),
    )

    statuses = sorted([to_boris.status_code, to_anna.status_code])
    assert statuses[0] == HTTPStatus.OK
    assert statuses[1] in (HTTPStatus.CONFLICT, HTTPStatus.NOT_FOUND)
    refused = to_anna if to_boris.status_code == HTTPStatus.OK else to_boris
    if refused.status_code == HTTPStatus.CONFLICT:
        assert_error(refused, 409, "last_administrator", LAST_ADMINISTRATOR)
    winner = anna if to_boris.status_code == HTTPStatus.OK else boris_client
    members = await list_members(winner)
    active_admins = [m for m in members if m["role"] == "administrator" and m["is_active"]]
    assert len(active_admins) == 1


@pytest.mark.parametrize("attempt", range(5))
async def test_fr16_two_administrators_deactivating_each_other_at_once_leave_one(
    factories: Factories, attempt: int
) -> None:
    # FR-16 clause «Two administrators acting at the same time SHALL NOT leave the organization
    # without one» (no scenario; the deactivation variant)
    anna, anna_account, boris_client, boris = await two_administrators(factories)

    to_boris, to_anna = await asyncio.gather(
        deactivate(anna, boris.user_id), deactivate(boris_client, anna_account.user_id)
    )

    statuses = sorted([to_boris.status_code, to_anna.status_code])
    assert statuses[0] == HTTPStatus.OK
    assert statuses[1] in (HTTPStatus.CONFLICT, HTTPStatus.UNAUTHORIZED, HTTPStatus.NOT_FOUND)
    refused = to_anna if to_boris.status_code == HTTPStatus.OK else to_boris
    if refused.status_code == HTTPStatus.CONFLICT:
        assert_error(refused, 409, "last_administrator", LAST_ADMINISTRATOR)
    winner = anna if to_boris.status_code == HTTPStatus.OK else boris_client
    members = await list_members(winner)
    active_admins = [m for m in members if m["role"] == "administrator" and m["is_active"]]
    assert len(active_admins) == 1
