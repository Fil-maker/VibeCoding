"""FR-11, FR-12 through the HTTP API: revoke, preview and accept an invitation."""

from datetime import timedelta

import pytest
from httpx import AsyncClient

from app.platform.mail import FakeMailSender
from tests.factories import (
    ANNA_EMAIL,
    API,
    PASSWORD,
    Factories,
    InvitationStatus,
    sign_in,
    token_from,
)
from tests.invitations_api import (
    BORIS,
    BORIS_PASSWORD,
    EMAIL_TAKEN,
    PASSWORD_MESSAGE,
    accept,
    assert_invalid_invitation,
    assert_no_user,
    invitation_mails,
    invite,
    listed,
    member_emails,
    preview,
)

# --- FR-11 Revoke an invitation ---


async def test_fr11_a_revoked_invitation_shows_revoked_and_its_link_stops_working(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-11 «Revoking»
    admin = await factories.signed_in(await factories.confirmed_admin())
    created = await invite(admin)
    token = token_from(invitation_mails(mail)[0])

    response = await admin.post(f"{API}/invitations/{created['id']}/revoke")

    assert response.status_code == 200
    assert response.json()["id"] == created["id"]
    assert response.json()["status"] == "revoked"
    assert [i["status"] for i in await listed(admin)] == ["revoked"]
    boris = await factories.open_client()
    await assert_invalid_invitation(boris, token)
    assert (await sign_in(boris, BORIS, BORIS_PASSWORD)).status_code == 401


async def test_fr11_a_not_sent_invitation_can_be_revoked(factories: Factories) -> None:
    # FR-11 «An administrator SHALL revoke an open invitation»
    admin = await factories.signed_in(await factories.confirmed_admin())
    not_sent = await factories.invitation(admin, "not_sent")

    response = await admin.post(f"{API}/invitations/{not_sent['id']}/revoke")

    assert response.status_code == 200
    assert response.json()["status"] == "revoked"


async def test_fr11_after_a_revoke_the_email_can_be_invited_again(factories: Factories) -> None:
    # FR-9 «open invitation»: a revoked invitation is not open
    admin = await factories.signed_in(await factories.confirmed_admin())
    await factories.invitation(admin, "revoked")

    response = await admin.post(f"{API}/invitations", json={"email": BORIS})

    assert response.status_code == 201
    assert response.json()["status"] == "sent"


async def test_fr11_revoking_an_accepted_invitation_changes_nothing(
    factories: Factories,
) -> None:
    # FR-11 «Revoking an accepted invitation»
    admin = await factories.signed_in(await factories.confirmed_admin())
    accepted = await factories.invitation(admin, "accepted")

    response = await admin.post(f"{API}/invitations/{accepted['id']}/revoke")

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert [i["status"] for i in await listed(admin)] == ["accepted"]
    boris = await factories.open_client()
    signed = await sign_in(boris, BORIS, PASSWORD)
    assert signed.status_code == 200
    assert signed.json()["organization"]["name"] == "ООО Ромашка"
    assert signed.json()["role"] == "employee"
    assert BORIS in await member_emails(admin)


@pytest.mark.parametrize("status", ["revoked", "expired"])
async def test_fr11_revoking_a_not_open_invitation_changes_nothing(
    factories: Factories, status: InvitationStatus
) -> None:
    # FR-11 «Revoking an invitation that is not open SHALL change nothing»
    admin = await factories.signed_in(await factories.confirmed_admin())
    invitation = await factories.invitation(admin, status)

    response = await admin.post(f"{API}/invitations/{invitation['id']}/revoke")

    assert response.status_code == 200
    assert response.json()["status"] == status
    assert [i["status"] for i in await listed(admin)] == [status]


# --- FR-12 Accept an invitation ---


async def test_fr12_a_valid_link_shows_the_organization_and_the_email(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-12: a valid link shows the organization name and the invited email
    admin = await factories.signed_in(await factories.confirmed_admin())
    await invite(admin)
    anonymous = await factories.open_client()

    response = await preview(anonymous, token_from(invitation_mails(mail)[0]))

    assert response.status_code == 200
    assert response.json() == {"organization_name": "ООО Ромашка", "email": BORIS}


async def test_fr12_a_garbage_token_is_invalid(client: AsyncClient) -> None:
    # FR-12 «A used, revoked, replaced or expired link»: an unknown token
    await assert_invalid_invitation(client, "not-a-real-token")


async def test_fr12_successful_acceptance_signs_the_employee_in(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-12 «Successful acceptance»
    admin = await factories.signed_in(await factories.confirmed_admin())
    await invite(admin)
    token = token_from(invitation_mails(mail)[0])
    factories.clock.advance(timedelta(days=3))
    boris = await factories.open_client()

    response = await accept(boris, token, "Борис Иванов", BORIS_PASSWORD)

    assert response.status_code == 200
    me = response.json()
    assert me["name"] == "Борис Иванов"
    assert me["email"] == BORIS
    assert me["role"] == "employee"
    assert me["organization"]["name"] == "ООО Ромашка"
    assert "vc_session" in boris.cookies
    current = await boris.get(f"{API}/auth/me")
    assert current.status_code == 200
    assert current.json()["user_id"] == me["user_id"]
    assert [(i["email"], i["status"]) for i in await listed(admin)] == [(BORIS, "accepted")]
    assert await member_emails(admin) == [ANNA_EMAIL, BORIS]


async def test_fr12_the_new_employee_can_sign_in_with_the_password(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-12 «become a confirmed, active employee»: no email confirmation is needed
    admin = await factories.signed_in(await factories.confirmed_admin())
    await invite(admin)
    await accept(await factories.open_client(), token_from(invitation_mails(mail)[0]))

    response = await sign_in(await factories.open_client(), BORIS, BORIS_PASSWORD)

    assert response.status_code == 200
    assert response.json()["role"] == "employee"


async def test_fr12_a_link_cannot_be_used_twice(factories: Factories, mail: FakeMailSender) -> None:
    # FR-12 «A used, revoked, replaced or expired link»: used
    admin = await factories.signed_in(await factories.confirmed_admin())
    await invite(admin)
    token = token_from(invitation_mails(mail)[0])
    assert (await accept(await factories.open_client(), token)).status_code == 200

    await assert_invalid_invitation(await factories.open_client(), token, "other-password-2")

    await assert_no_user(factories, BORIS, "other-password-2")
    assert [i["status"] for i in await listed(admin)] == ["accepted"]


async def test_fr12_a_revoked_link_creates_no_user(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-12 «A used, revoked, replaced or expired link»: revoked
    admin = await factories.signed_in(await factories.confirmed_admin())
    await invite(admin)
    token = token_from(invitation_mails(mail)[0])
    invitation_id = (await listed(admin))[0]["id"]
    await admin.post(f"{API}/invitations/{invitation_id}/revoke")

    boris = await factories.open_client()
    await assert_invalid_invitation(boris, token)

    await assert_no_user(factories, BORIS, BORIS_PASSWORD)


async def test_fr12_a_replaced_link_creates_no_user(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-12 «A used, revoked, replaced or expired link»: replaced by a resend
    admin = await factories.signed_in(await factories.confirmed_admin())
    created = await invite(admin)
    old_token = token_from(invitation_mails(mail)[0])
    await admin.post(f"{API}/invitations/{created['id']}/resend")

    boris = await factories.open_client()
    await assert_invalid_invitation(boris, old_token)

    await assert_no_user(factories, BORIS, BORIS_PASSWORD)


async def test_fr12_an_expired_link_creates_no_user(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-12 «A used, revoked, replaced or expired link»: 8 days old
    admin = await factories.signed_in(await factories.confirmed_admin())
    await invite(admin)
    token = token_from(invitation_mails(mail)[0])
    factories.clock.advance(timedelta(days=8))

    boris = await factories.open_client()
    await assert_invalid_invitation(boris, token)

    await assert_no_user(factories, BORIS, BORIS_PASSWORD)
    assert [i["status"] for i in await listed(admin)] == ["expired"]


async def test_fr12_the_email_that_became_a_user_meanwhile_does_not_join(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-12 «The email became a user meanwhile»
    anna = await factories.signed_in(await factories.confirmed_admin())
    vera = await factories.signed_in(
        await factories.confirmed_admin(email="vera@lyutik.test", organization_name="Лютик")
    )
    await invite(anna)
    await invite(vera)
    romashka_token, lyutik_token = (token_from(m) for m in invitation_mails(mail))
    boris = await factories.open_client()
    joined = await accept(boris, lyutik_token)
    assert joined.status_code == 200
    assert joined.json()["organization"]["name"] == "Лютик"

    late = await accept(await factories.open_client(), romashka_token, "Борис Другой")

    assert late.status_code == 409
    assert late.json()["error"]["code"] == "email_taken"
    assert late.json()["error"]["message"] == EMAIL_TAKEN
    me = await boris.get(f"{API}/auth/me")
    assert me.json()["organization"]["name"] == "Лютик"
    assert me.json()["name"] == "Борис Иванов"
    signed = await sign_in(await factories.open_client(), BORIS, BORIS_PASSWORD)
    assert signed.status_code == 200
    assert signed.json()["organization"]["name"] == "Лютик"
    assert await member_emails(anna) == [ANNA_EMAIL]
    assert BORIS in await member_emails(vera)


@pytest.mark.parametrize(
    ("overrides", "field", "message"),
    [
        ({"name": ""}, "name", "Укажите имя"),
        ({"name": "я" * 201}, "name", "Укажите имя"),
        ({"password": "x" * 9}, "password", PASSWORD_MESSAGE),
        ({"password": "x" * 129}, "password", PASSWORD_MESSAGE),
    ],
)
async def test_fr12_values_outside_the_limits_are_refused_and_create_no_user(
    factories: Factories,
    mail: FakeMailSender,
    overrides: dict[str, str],
    field: str,
    message: str,
) -> None:
    # FR-12 «name (1-200 characters) and a password of 10-128 characters»
    admin = await factories.signed_in(await factories.confirmed_admin())
    await invite(admin)
    token = token_from(invitation_mails(mail)[0])
    body = {"token": token, "name": "Борис Иванов", "password": BORIS_PASSWORD, **overrides}
    boris = await factories.open_client()

    response = await boris.post(f"{API}/invitations/accept", json=body)

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert response.json()["error"]["fields"] == {field: message}
    assert "vc_session" not in boris.cookies
    await assert_no_user(factories, BORIS, body["password"])
    assert [i["status"] for i in await listed(admin)] == ["sent"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"name": "я" * 200},
        {"name": "я"},
        {"password": "x" * 10},
        {"password": "x" * 128},
    ],
)
async def test_fr12_values_on_the_limits_are_accepted(
    factories: Factories, mail: FakeMailSender, overrides: dict[str, str]
) -> None:
    # FR-12 «name (1-200 characters) and a password of 10-128 characters»
    admin = await factories.signed_in(await factories.confirmed_admin())
    await invite(admin)
    token = token_from(invitation_mails(mail)[0])
    body = {"token": token, "name": "Борис Иванов", "password": BORIS_PASSWORD, **overrides}

    response = await (await factories.open_client()).post(f"{API}/invitations/accept", json=body)

    assert response.status_code == 200
