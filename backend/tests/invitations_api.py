"""Helpers shared by the invitation tests (FR-9 … FR-12)."""

from http import HTTPStatus
from typing import Any

from httpx import AsyncClient

from app.platform.mail import FakeMailSender, OutgoingEmail
from tests.factories import API, Factories, sign_in

BORIS = "boris@romashka.test"
INVALID_INVITATION = "Приглашение недействительно или устарело"
EMAIL_TAKEN = "Этот email уже зарегистрирован"
EXISTS = "Приглашение на этот email уже отправлено"
NOT_OPEN = "Приглашение уже принято, отозвано или истекло"
PASSWORD_MESSAGE = "Пароль должен быть от 10 до 128 символов"
BORIS_PASSWORD = "boris-password-1"


def invitation_mails(mail: FakeMailSender) -> list[OutgoingEmail]:
    """The invitation emails sent so far."""
    return [m for m in mail.sent if m.subject.startswith("Приглашение в ")]


async def invite(admin: AsyncClient, email: str = BORIS) -> dict[str, Any]:
    """POST /invitations that must succeed; returns the invitation."""
    response = await admin.post(f"{API}/invitations", json={"email": email})
    assert response.status_code == HTTPStatus.CREATED
    return response.json()


async def listed(admin: AsyncClient) -> list[dict[str, Any]]:
    """The items of GET /invitations."""
    response = await admin.get(f"{API}/invitations")
    assert response.status_code == HTTPStatus.OK
    return response.json()["items"]


async def preview(client: AsyncClient, token: str) -> Any:
    """POST /invitations/preview."""
    return await client.post(f"{API}/invitations/preview", json={"token": token})


async def accept(
    client: AsyncClient,
    token: str,
    name: str = "Борис Иванов",
    password: str = BORIS_PASSWORD,
) -> Any:
    """POST /invitations/accept."""
    return await client.post(
        f"{API}/invitations/accept", json={"token": token, "name": name, "password": password}
    )


async def assert_no_user(factories: Factories, email: str, password: str) -> None:
    """Nobody can sign in with this email and password: no user was created."""
    response = await sign_in(await factories.open_client(), email, password)
    assert response.status_code == HTTPStatus.UNAUTHORIZED
    assert response.json()["error"]["code"] == "invalid_credentials"


async def assert_invalid_invitation(
    client: AsyncClient, token: str, password: str = BORIS_PASSWORD
) -> None:
    """The link is refused on preview and on accept."""
    previewed = await preview(client, token)
    accepted = await accept(client, token, password=password)
    for response in (previewed, accepted):
        assert response.status_code == HTTPStatus.BAD_REQUEST
        assert response.json()["error"]["code"] == "invalid_invitation"
        assert response.json()["error"]["message"] == INVALID_INVITATION


async def member_emails(admin: AsyncClient) -> list[str]:
    """The emails of GET /members, in the order of the list."""
    response = await admin.get(f"{API}/members")
    assert response.status_code == HTTPStatus.OK
    return [m["email"] for m in response.json()["items"]]
