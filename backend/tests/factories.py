"""Small factories: users and sessions, built through the public API."""

import re
from contextlib import AsyncExitStack
from dataclasses import dataclass
from http import HTTPStatus
from typing import Any

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient, Response

from app.modules.mailboxes.service import read_due_mailboxes
from app.platform.mail import FakeMailSender, OutgoingEmail
from app.platform.mail_reader import FakeMailReader
from app.platform.settings import Settings
from tests.settable_clock import SettableClock

API = "/api/v1"
APP_BASE_URL = "http://localhost:5173"
PASSWORD = "correct-horse-1"
ANNA_EMAIL = "anna@romashka.test"
VERA_EMAIL = "vera@romashka.test"
APP_PASSWORD = "app-pass-1234"
# A valid Fernet key (32 bytes, url-safe base64) used only by tests.
TEST_ENCRYPTION_KEY = "MDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDAwMDA="


def settings_for(database_url: str) -> Settings:
    """Settings of the test app."""
    return Settings(
        database_url=database_url,
        app_base_url=APP_BASE_URL,
        mail_from="noreply@vibecoding.test",
        smtp_host="localhost",
        mailbox_encryption_key=TEST_ENCRYPTION_KEY,
        mailbox_reading_enabled=False,
    )


def token_from(email: OutgoingEmail) -> str:
    """The one-time token of the link in an email body."""
    match = re.search(r"#token=([A-Za-z0-9_\-]+)", email.text)
    assert match is not None, f"no link with a token in: {email.text}"
    return match.group(1)


@dataclass(frozen=True)
class Account:
    """A user the factories created."""

    email: str
    password: str
    name: str
    user_id: str = ""


def registration_body(
    *,
    email: str = ANNA_EMAIL,
    password: str = PASSWORD,
    name: str = "Анна Петрова",
) -> dict[str, str]:
    """A valid body of POST /auth/registrations."""
    return {
        "name": name,
        "email": email,
        "password": password,
    }


async def sign_in(client: AsyncClient, email: str, password: str) -> Response:
    """POST /auth/sessions."""
    return await client.post(f"{API}/auth/sessions", json={"email": email, "password": password})


class Factories:
    """Builds data through HTTP with the mail and the clock the test controls."""

    def __init__(
        self, app: FastAPI, mail: FakeMailSender, clock: SettableClock, reader: FakeMailReader
    ) -> None:
        self.app = app
        self.mail = mail
        self.clock = clock
        self.reader = reader
        self._stack = AsyncExitStack()

    async def open_client(self, origin: str | None = APP_BASE_URL) -> AsyncClient:
        """A new client with its own cookies; it sends `origin` as the Origin header when given."""
        headers = {} if origin is None else {"Origin": origin}
        client = AsyncClient(
            transport=ASGITransport(app=self.app), base_url="http://test", headers=headers
        )
        return await self._stack.enter_async_context(client)

    async def close(self) -> None:
        """Close every client that was opened."""
        await self._stack.aclose()

    async def unconfirmed_user(
        self,
        *,
        email: str = ANNA_EMAIL,
        password: str = PASSWORD,
        name: str = "Анна Петрова",
    ) -> Account:
        """Register a user; the confirmation email is the last one in `mail.sent`."""
        client = await self.open_client()
        response = await client.post(
            f"{API}/auth/registrations",
            json=registration_body(email=email, password=password, name=name),
        )
        assert response.status_code == HTTPStatus.CREATED
        return Account(email.strip().lower(), password, name)

    async def confirmed_user(
        self,
        *,
        email: str = ANNA_EMAIL,
        password: str = PASSWORD,
        name: str = "Анна Петрова",
    ) -> Account:
        """Register a user and confirm the email."""
        account = await self.unconfirmed_user(email=email, password=password, name=name)
        client = await self.open_client()
        response = await client.post(
            f"{API}/auth/email-confirmations",
            json={"token": token_from(self.mail.sent[-1])},
        )
        assert response.status_code == HTTPStatus.OK
        return Account(account.email, password, name, response.json()["user_id"])

    async def signed_in(self, account: Account) -> AsyncClient:
        """A new client signed in as `account`: one session."""
        client = await self.open_client()
        response = await sign_in(client, account.email, account.password)
        assert response.status_code == HTTPStatus.OK
        return client

    async def connect_mailbox(
        self,
        client: AsyncClient,
        login: str,
        *,
        server: str = "imap.yandex.ru",
        port: int = 993,
        password: str = APP_PASSWORD,
    ) -> dict[str, Any]:
        """Connect a mailbox through the API (the fake reader accepts it); returns the `Mailbox`."""
        response = await client.post(
            f"{API}/mailboxes",
            json={"server": server, "port": port, "login": login, "password": password},
        )
        assert response.status_code == HTTPStatus.CREATED, response.text
        mailbox: dict[str, Any] = response.json()
        return mailbox

    async def read_due(self) -> int:
        """Run one reading pass over the mailboxes that are due; returns how many were read."""
        return await read_due_mailboxes(
            self.app.state.database, self.reader, self.clock, self.app.state.settings
        )


async def list_mailboxes(client: AsyncClient) -> list[dict[str, Any]]:
    """GET /mailboxes of a signed-in client."""
    response = await client.get(f"{API}/mailboxes")
    assert response.status_code == HTTPStatus.OK, response.text
    mailboxes: list[dict[str, Any]] = response.json()
    return mailboxes


async def list_chains(client: AsyncClient, *, limit: int = 100) -> list[dict[str, Any]]:
    """GET /reply-chains: the first page of summaries, latest email first."""
    response = await client.get(f"{API}/reply-chains", params={"limit": limit})
    assert response.status_code == HTTPStatus.OK, response.text
    items: list[dict[str, Any]] = response.json()["items"]
    return items


async def open_chain(client: AsyncClient, chain_id: str) -> dict[str, Any]:
    """GET /reply-chains/{id}."""
    response = await client.get(f"{API}/reply-chains/{chain_id}")
    assert response.status_code == HTTPStatus.OK, response.text
    chain: dict[str, Any] = response.json()
    return chain


async def count_emails(client: AsyncClient) -> int:
    """How many emails the user has: the sum over the first 100 chains."""
    return sum(chain["email_count"] for chain in await list_chains(client))
