"""FR-9 through the HTTP API: invite an employee."""

from datetime import datetime, timedelta

from httpx import AsyncClient

from app.platform.mail import FakeMailSender
from tests.factories import ANNA_EMAIL, API, PASSWORD, Factories, sign_in, token_from
from tests.invitations_api import (
    BORIS,
    EMAIL_TAKEN,
    EXISTS,
    invitation_mails,
    invite,
    listed,
    member_emails,
)
from tests.settable_clock import CLOCK_START


async def test_fr9_successful_invitation_is_listed_as_sent_and_one_email_goes_out(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-9 «Successful invitation»
    admin = await factories.signed_in(await factories.confirmed_admin())

    response = await admin.post(f"{API}/invitations", json={"email": BORIS})

    assert response.status_code == 201
    created = response.json()
    assert created["email"] == BORIS
    assert created["status"] == "sent"
    assert datetime.fromisoformat(created["sent_at"]) == CLOCK_START
    assert datetime.fromisoformat(created["expires_at"]) == CLOCK_START + timedelta(days=7)
    items = await listed(admin)
    assert [(i["id"], i["email"], i["status"]) for i in items] == [(created["id"], BORIS, "sent")]
    mails = invitation_mails(mail)
    assert len(mails) == 1
    assert mails[0].to == BORIS
    assert mails[0].subject == "Приглашение в ООО Ромашка — VibeCoding"
    assert token_from(mails[0])


async def test_fr9_email_of_a_confirmed_user_of_another_organization_is_refused(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-9 «The email is already a user»
    await factories.confirmed_admin(email="vera@lyutik.test", organization_name="Лютик")
    admin = await factories.signed_in(await factories.confirmed_admin())

    response = await admin.post(f"{API}/invitations", json={"email": "vera@lyutik.test"})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"
    assert response.json()["error"]["message"] == EMAIL_TAKEN
    assert await listed(admin) == []
    assert invitation_mails(mail) == []


async def test_fr9_email_of_a_user_of_the_own_organization_is_refused(
    factories: Factories,
) -> None:
    # FR-9 «The email is already a user»: a confirmed user of any organization
    admin = await factories.signed_in(await factories.confirmed_admin())

    response = await admin.post(f"{API}/invitations", json={"email": ANNA_EMAIL})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "email_taken"
    assert await listed(admin) == []


async def test_fr9_a_second_invitation_while_the_first_is_open_is_refused(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-9 «A repeated invitation»
    admin = await factories.signed_in(await factories.confirmed_admin())
    first = await invite(admin)

    response = await admin.post(f"{API}/invitations", json={"email": BORIS})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invitation_exists"
    assert response.json()["error"]["message"] == EXISTS
    assert [i["id"] for i in await listed(admin)] == [first["id"]]
    assert len(invitation_mails(mail)) == 1


async def test_fr9_a_not_sent_invitation_is_still_open_for_a_repeat(
    factories: Factories,
) -> None:
    # FR-9 «A repeated invitation»: an invitation that was not sent is open too
    admin = await factories.signed_in(await factories.confirmed_admin())
    await factories.invitation(admin, "not_sent")

    response = await admin.post(f"{API}/invitations", json={"email": BORIS})

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invitation_exists"


async def test_fr9_two_organizations_may_have_an_open_invitation_for_one_email(
    factories: Factories,
) -> None:
    # FR-9 «A repeated invitation»: the refusal is per organization
    anna = await factories.signed_in(await factories.confirmed_admin())
    lyutik = await factories.signed_in(
        await factories.confirmed_admin(email="vera@lyutik.test", organization_name="Лютик")
    )
    await invite(anna)

    response = await lyutik.post(f"{API}/invitations", json={"email": BORIS})

    assert response.status_code == 201


async def test_fr9_an_invalid_email_is_refused(factories: Factories, mail: FakeMailSender) -> None:
    # FR-9 «Invite an employee»: the form validation of the email
    admin = await factories.signed_in(await factories.confirmed_admin())

    response = await admin.post(f"{API}/invitations", json={"email": "no-at-sign"})

    assert response.status_code == 422
    assert response.json()["error"]["code"] == "validation_failed"
    assert response.json()["error"]["fields"] == {"email": "Укажите корректный email"}
    assert invitation_mails(mail) == []


async def test_fr9_inviting_without_a_session_is_refused(client: AsyncClient) -> None:
    # Interface: POST /invitations is for the administrator; 401 not_signed_in without a session
    response = await client.post(f"{API}/invitations", json={"email": BORIS})

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_signed_in"


async def test_fr9_the_domain_does_not_grant_membership(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-9 «The domain does not grant membership»
    anna = await factories.signed_in(await factories.confirmed_admin())
    await factories.unconfirmed_admin(email="gleb@romashka.test", organization_name="Глеб")
    gleb_client = await factories.open_client()
    confirmed = await gleb_client.post(
        f"{API}/auth/email-confirmations", json={"token": token_from(mail.sent[-1])}
    )
    signed = await sign_in(await factories.open_client(), "gleb@romashka.test", PASSWORD)

    assert confirmed.status_code == 200
    assert signed.status_code == 200
    for me in (confirmed.json(), signed.json()):
        assert me["organization"]["name"] != "ООО Ромашка"
    assert await member_emails(anna) == [ANNA_EMAIL]
