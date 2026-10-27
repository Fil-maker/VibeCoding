"""FR-10 through the HTTP API: invitation status, resending and the list."""

from datetime import datetime, timedelta

import pytest
from httpx import AsyncClient

from app.platform.mail import FakeMailSender
from tests.factories import API, Factories, InvitationStatus, token_from
from tests.invitations_api import (
    BORIS,
    NOT_OPEN,
    assert_invalid_invitation,
    invitation_mails,
    invite,
    listed,
    preview,
)
from tests.settable_clock import CLOCK_START, SettableClock


async def test_fr10_a_mail_failure_leaves_the_invitation_not_sent(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-10 «The mail server is unavailable»
    admin = await factories.signed_in(await factories.confirmed_admin())
    mail.fail_next(1)

    response = await admin.post(f"{API}/invitations", json={"email": BORIS})

    assert response.status_code == 201
    assert response.json()["status"] == "not_sent"
    assert response.json()["sent_at"] is None
    items = await listed(admin)
    assert [(i["email"], i["status"], i["sent_at"]) for i in items] == [(BORIS, "not_sent", None)]
    assert invitation_mails(mail) == []


async def test_fr10_resending_a_not_sent_invitation_sends_a_new_email(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-10 «Resending»: after the mail server is back
    admin = await factories.signed_in(await factories.confirmed_admin())
    not_sent = await factories.invitation(admin, "not_sent")

    response = await admin.post(f"{API}/invitations/{not_sent['id']}/resend")

    assert response.status_code == 200
    assert response.json()["id"] == not_sent["id"]
    assert response.json()["status"] == "sent"
    assert [i["status"] for i in await listed(admin)] == ["sent"]
    mails = invitation_mails(mail)
    assert len(mails) == 1
    assert mails[0].to == BORIS
    anonymous = await factories.open_client()
    assert (await preview(anonymous, token_from(mails[0]))).status_code == 200


async def test_fr10_resending_replaces_the_earlier_link(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-10 «Resending»: the earlier link shows the invalid-invitation message
    admin = await factories.signed_in(await factories.confirmed_admin())
    first = await invite(admin)
    old_token = token_from(invitation_mails(mail)[0])
    factories.clock.advance(timedelta(days=2))

    response = await admin.post(f"{API}/invitations/{first['id']}/resend")

    assert response.status_code == 200
    assert response.json()["status"] == "sent"
    assert datetime.fromisoformat(response.json()["expires_at"]) == (
        CLOCK_START + timedelta(days=2) + timedelta(days=7)
    )
    mails = invitation_mails(mail)
    assert len(mails) == 2
    assert mails[1].to == BORIS
    new_token = token_from(mails[1])
    assert new_token != old_token
    anonymous = await factories.open_client()
    await assert_invalid_invitation(anonymous, old_token)
    previewed = await preview(anonymous, new_token)
    assert previewed.status_code == 200
    assert len(await listed(admin)) == 1


async def test_fr10_resend_with_the_mail_server_down_keeps_the_invitation_not_sent(
    factories: Factories, mail: FakeMailSender
) -> None:
    # FR-10: a mail failure leaves the invitation «Не отправлено»
    admin = await factories.signed_in(await factories.confirmed_admin())
    not_sent = await factories.invitation(admin, "not_sent")
    mail.fail_next(1)

    response = await admin.post(f"{API}/invitations/{not_sent['id']}/resend")

    assert response.status_code == 200
    assert response.json()["status"] == "not_sent"
    assert [i["status"] for i in await listed(admin)] == ["not_sent"]
    assert invitation_mails(mail) == []


@pytest.mark.parametrize("status", ["accepted", "revoked", "expired"])
async def test_fr10_a_not_open_invitation_cannot_be_resent(
    factories: Factories, mail: FakeMailSender, status: InvitationStatus
) -> None:
    # FR-10 «An expired invitation»: only an open invitation can be resent
    admin = await factories.signed_in(await factories.confirmed_admin())
    invitation = await factories.invitation(admin, status)
    mails_before = len(invitation_mails(mail))

    response = await admin.post(f"{API}/invitations/{invitation['id']}/resend")

    assert response.status_code == 409
    assert response.json()["error"]["code"] == "invitation_not_open"
    assert response.json()["error"]["message"] == NOT_OPEN
    assert len(invitation_mails(mail)) == mails_before
    assert [i["status"] for i in await listed(admin)] == [status]


async def test_fr10_an_unknown_invitation_cannot_be_resent_or_revoked(
    factories: Factories,
) -> None:
    # Interface: resend and revoke answer 404 not_found for an unknown id
    admin = await factories.signed_in(await factories.confirmed_admin())
    real = await invite(admin)
    assert (await admin.post(f"{API}/invitations/{real['id']}/revoke")).status_code == 200
    unknown = "00000000-0000-0000-0000-000000000001"

    resent = await admin.post(f"{API}/invitations/{unknown}/resend")
    revoked = await admin.post(f"{API}/invitations/{unknown}/revoke")

    for response in (resent, revoked):
        assert response.status_code == 404
        assert response.json()["error"]["code"] == "not_found"
        assert response.json()["error"]["message"] == "Не найдено"


async def test_fr10_an_invitation_shows_expired_after_8_days(factories: Factories) -> None:
    # FR-10 «An expired invitation»
    admin = await factories.signed_in(await factories.confirmed_admin())
    await invite(admin)

    factories.clock.advance(timedelta(days=8))

    items = await listed(admin)
    assert [(i["email"], i["status"]) for i in items] == [(BORIS, "expired")]


async def test_fr9_an_invitation_is_still_sent_just_before_7_days(
    factories: Factories,
) -> None:
    # FR-9 «a link valid for 7 days»
    admin = await factories.signed_in(await factories.confirmed_admin())
    await invite(admin)

    factories.clock.advance(timedelta(days=6, hours=23))

    assert [i["status"] for i in await listed(admin)] == ["sent"]


async def test_fr10_the_list_is_newest_first(factories: Factories, clock: SettableClock) -> None:
    # FR-10 «newest first»
    admin = await factories.signed_in(await factories.confirmed_admin())
    emails = ["a@romashka.test", "b@romashka.test", "c@romashka.test"]
    for email in emails:
        await invite(admin, email)
        clock.advance(timedelta(minutes=1))

    items = await listed(admin)

    assert [i["email"] for i in items] == ["c@romashka.test", "b@romashka.test", "a@romashka.test"]
    sent_at = [datetime.fromisoformat(i["sent_at"]) for i in items]
    assert sent_at == [CLOCK_START + timedelta(minutes=m) for m in (2, 1, 0)]


async def test_fr10_the_list_is_paged_by_limit_and_cursor(factories: Factories) -> None:
    # Interface: Page[Invitation] with limit and cursor
    admin = await factories.signed_in(await factories.confirmed_admin())
    for email in ["a@romashka.test", "b@romashka.test", "c@romashka.test"]:
        await invite(admin, email)
        factories.clock.advance(timedelta(minutes=1))

    first = (await admin.get(f"{API}/invitations", params={"limit": 2})).json()
    second = (
        await admin.get(f"{API}/invitations", params={"limit": 2, "cursor": first["next_cursor"]})
    ).json()

    assert [i["email"] for i in first["items"]] == ["c@romashka.test", "b@romashka.test"]
    assert first["next_cursor"] is not None
    assert [i["email"] for i in second["items"]] == ["a@romashka.test"]
    assert second["next_cursor"] is None


async def test_fr10_listing_without_a_session_is_refused(client: AsyncClient) -> None:
    # Interface: GET /invitations answers 401 without a session
    response = await client.get(f"{API}/invitations")

    assert response.status_code == 401
    assert response.json()["error"]["code"] == "not_signed_in"
