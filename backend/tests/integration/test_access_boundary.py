"""FR-17 … FR-20 through the HTTP API: sessions, organizations, roles and the Origin."""

from dataclasses import dataclass
from http import HTTPStatus

import pytest
from httpx import AsyncClient, Response

from app.platform.mail import FakeMailSender
from tests.factories import ANNA_EMAIL, API, Factories
from tests.invitations_api import invitation_mails, listed
from tests.members_api import (
    BORIS_EMAIL,
    DINA_EMAIL,
    NOT_FOUND,
    UNKNOWN_ID,
    VERA_EMAIL,
    assert_error,
    deactivate,
    list_members,
    member_of,
)

# (method, path template, body) of every administrator route; {anna}, {dina}, {invitation}
ADMIN_ROUTES = [
    ("GET", "/invitations", None),
    ("POST", "/invitations", {"email": "gleb@romashka.test"}),
    ("POST", "/invitations/{invitation}/resend", None),
    ("POST", "/invitations/{invitation}/revoke", None),
    ("GET", "/members", None),
    ("POST", "/members/{anna}/deactivate", None),
    ("POST", "/members/{dina}/reactivate", None),
    ("PUT", "/members/{anna}/role", {"role": "employee"}),
    ("PUT", "/members/{dina}/role", {"role": "administrator"}),
]


@dataclass
class Boundary:
    """«ООО Ромашка» (Анна, Борис, inactive Дина, an open invitation) and «Лютик» (Вера)."""

    anna: AsyncClient
    boris: AsyncClient
    vera: AsyncClient
    anna_id: str
    boris_id: str
    dina_id: str
    invitation_id: str

    def path(self, template: str) -> str:
        """The route with the ids of «ООО Ромашка» filled in."""
        return f"{API}{template}".format(
            anna=self.anna_id, boris=self.boris_id, dina=self.dina_id, invitation=self.invitation_id
        )


@pytest.fixture
async def world(factories: Factories) -> Boundary:
    """The two organizations the negative cases use."""
    anna_account = await factories.confirmed_admin()
    anna = await factories.signed_in(anna_account)
    boris_account = await factories.employee(anna, email=BORIS_EMAIL)
    dina = await factories.employee(anna, email=DINA_EMAIL, name="Дина Орлова", active=False)
    created = await anna.post(f"{API}/invitations", json={"email": "elena@romashka.test"})
    assert created.status_code == HTTPStatus.CREATED
    vera = await factories.signed_in(
        await factories.confirmed_admin(email=VERA_EMAIL, organization_name="Лютик", name="Вера")
    )
    return Boundary(
        anna=anna,
        boris=await factories.signed_in(boris_account),
        vera=vera,
        anna_id=anna_account.user_id,
        boris_id=boris_account.user_id,
        dina_id=dina.user_id,
        invitation_id=created.json()["id"],
    )


ROMASHKA_INVITATIONS = {
    (BORIS_EMAIL, "accepted"),
    (DINA_EMAIL, "accepted"),
    ("elena@romashka.test", "sent"),
}


async def romashka_invitations(world: Boundary) -> set[tuple[str, str]]:
    """The invitations of «ООО Ромашка» as (email, status); the order is not part of the check."""
    return {(i["email"], i["status"]) for i in await listed(world.anna)}


async def assert_romashka_unchanged(world: Boundary, mail: FakeMailSender, mails: int) -> None:
    """Nothing changed in «ООО Ромашка»: members, roles, states, the invitation and the mail."""
    members = {m["email"]: m for m in await list_members(world.anna)}
    assert {e: (m["role"], m["is_active"]) for e, m in members.items()} == {
        ANNA_EMAIL: ("administrator", True),
        BORIS_EMAIL: ("employee", True),
        DINA_EMAIL: ("employee", False),
    }
    assert await romashka_invitations(world) == ROMASHKA_INVITATIONS
    assert len(invitation_mails(mail)) == mails
    assert (await world.boris.get(f"{API}/auth/me")).status_code == HTTPStatus.OK


# --- FR-19 Administrator actions are closed to employees ---


@pytest.mark.parametrize(("method", "template", "body"), ADMIN_ROUTES)
async def test_fr19_an_employee_gets_not_found_on_every_administrator_route(
    world: Boundary, mail: FakeMailSender, method: str, template: str, body: dict[str, str] | None
) -> None:
    # FR-19 «An employee calls an administrator action»
    mails_before = len(invitation_mails(mail))

    response = await world.boris.request(method, world.path(template), json=body)

    assert_error(response, 404, "not_found", NOT_FOUND)
    await assert_romashka_unchanged(world, mail, mails_before)


async def test_fr19_an_employee_inviting_creates_no_invitation(
    world: Boundary, mail: FakeMailSender
) -> None:
    # FR-19 «An employee calls an administrator action»: invites «gleb@romashka.test»
    response = await world.boris.post(f"{API}/invitations", json={"email": "gleb@romashka.test"})

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert await romashka_invitations(world) == ROMASHKA_INVITATIONS
    assert all(m.to != "gleb@romashka.test" for m in mail.sent)


# --- FR-18 Organizations never see each other ---


@pytest.mark.parametrize(
    ("method", "template", "body"),
    [r for r in ADMIN_ROUTES if "{" in r[1]],
)
async def test_fr18_another_organizations_administrator_gets_not_found_by_identifier(
    world: Boundary, mail: FakeMailSender, method: str, template: str, body: dict[str, str] | None
) -> None:
    # FR-18 «An administrator reaches into another organization»
    mails_before = len(invitation_mails(mail))
    own_template = template.format(
        anna=UNKNOWN_ID, dina=UNKNOWN_ID, invitation=UNKNOWN_ID, boris=UNKNOWN_ID
    )

    response = await world.vera.request(method, world.path(template), json=body)

    unknown = await world.vera.request(method, f"{API}{own_template}", json=body)
    assert_error(response, 404, "not_found", NOT_FOUND)
    assert response.json() == unknown.json()
    await assert_romashka_unchanged(world, mail, mails_before)


async def test_fr18_deactivating_boris_of_another_organization_changes_nothing(
    world: Boundary, mail: FakeMailSender
) -> None:
    # FR-18 «An administrator reaches into another organization»: Вера deactivates Борис
    mails_before = len(invitation_mails(mail))

    response = await deactivate(world.vera, world.boris_id)

    assert_error(response, 404, "not_found", NOT_FOUND)
    assert (await member_of(world.anna, world.boris_id))["is_active"] is True
    assert (await world.boris.get(f"{API}/auth/me")).status_code == HTTPStatus.OK
    await assert_romashka_unchanged(world, mail, mails_before)


async def test_fr18_the_lists_hold_only_the_own_organization(world: Boundary) -> None:
    # FR-18 / FR-13: members and invitations of the other organization never appear
    assert [m["email"] for m in await list_members(world.vera)] == [VERA_EMAIL]
    assert await listed(world.vera) == []


async def test_fr18_an_organization_named_in_the_request_is_refused(
    world: Boundary, mail: FakeMailSender
) -> None:
    # FR-18 «An organization named in the request is ignored»
    romashka_id = (await world.anna.get(f"{API}/auth/me")).json()["organization"]["id"]
    mails_before = len(invitation_mails(mail))

    response = await world.vera.post(
        f"{API}/invitations",
        json={"email": "gleb@romashka.test", "organization_id": romashka_id},
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["error"]["code"] == "validation_failed"
    assert await romashka_invitations(world) == ROMASHKA_INVITATIONS
    assert await listed(world.vera) == []
    assert len(invitation_mails(mail)) == mails_before


# --- FR-17 Protected pages and actions need a signed-in user ---


@pytest.mark.parametrize(("method", "template", "body"), ADMIN_ROUTES)
async def test_fr17_a_signed_out_request_to_an_administrator_route_is_refused(
    world: Boundary,
    client: AsyncClient,
    mail: FakeMailSender,
    method: str,
    template: str,
    body: dict[str, str] | None,
) -> None:
    # FR-17: a request without a valid session is refused as signed out
    mails_before = len(invitation_mails(mail))

    response = await client.request(method, world.path(template), json=body)

    assert_error(response, 401, "not_signed_in", "Войдите в систему")
    await assert_romashka_unchanged(world, mail, mails_before)


@pytest.mark.parametrize("path", ["/members", "/invitations", "/auth/me"])
async def test_fr17_a_forged_session_token_returns_no_data(factories: Factories, path: str) -> None:
    # FR-17 «A forged or ended session»: a token that never existed
    await factories.confirmed_admin()
    forged = await factories.open_client()
    forged.cookies.set("vc_session", "forged-token-that-never-existed")

    response = await forged.get(f"{API}{path}")

    assert_error(response, 401, "not_signed_in", "Войдите в систему")


@pytest.mark.parametrize("path", ["/members", "/invitations", "/auth/me"])
async def test_fr17_a_session_ended_by_sign_out_returns_no_data(
    factories: Factories, path: str
) -> None:
    # FR-17 «A forged or ended session»: a session ended by sign-out
    admin = await factories.signed_in(await factories.confirmed_admin())
    cookie = admin.cookies["vc_session"]
    alive = await factories.open_client()
    alive.cookies.set("vc_session", cookie)
    assert (await alive.get(f"{API}/auth/me")).status_code == HTTPStatus.OK
    assert (await admin.delete(f"{API}/auth/sessions/current")).status_code == HTTPStatus.NO_CONTENT
    replay = await factories.open_client()
    replay.cookies.set("vc_session", cookie)
    assert (await admin.get(f"{API}/auth/me")).status_code == HTTPStatus.UNAUTHORIZED

    response: Response = await replay.get(f"{API}{path}")

    assert_error(response, 401, "not_signed_in", "Войдите в систему")


# --- FR-20 Actions from other sites are refused ---


async def test_fr20_a_cross_site_form_with_the_session_creates_no_invitation(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-20 «A cross-site form»
    anna = await factories.signed_in(await factories.confirmed_admin())
    mails_before = len(mail.sent)
    attacker_page = await factories.open_client(origin="http://attacker.test")
    attacker_page.cookies.set("vc_session", anna.cookies["vc_session"])

    response = await attacker_page.post(f"{API}/invitations", json={"email": "evil@attacker.test"})

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()["error"]["code"] == "forbidden_origin"
    assert await listed(anna) == []
    assert len(mail.sent) == mails_before
