"""Outgoing service emails: a sender protocol, the SMTP sender and a fake for tests."""

from dataclasses import dataclass, field
from email.message import EmailMessage
from typing import Protocol

import aiosmtplib
from fastapi import Request

from app.platform.settings import Settings

SMTP_TIMEOUT_SECONDS = 10.0


class MailDeliveryError(Exception):
    """The mail server did not accept the message."""


@dataclass(frozen=True)
class OutgoingEmail:
    """A plain-text service email."""

    to: str
    subject: str
    text: str


class MailSender(Protocol):
    """Sends service emails; the app never touches a user's mailbox through it."""

    async def send(self, email: OutgoingEmail) -> None:
        """Send the email; raise `MailDeliveryError` on failure."""
        ...


class SmtpMailSender:
    """Sends through the SMTP server of the settings."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    async def send(self, email: OutgoingEmail) -> None:
        """Send the email with a timeout; any transport failure becomes `MailDeliveryError`."""
        message = EmailMessage()
        message["From"] = self._settings.mail_from
        message["To"] = email.to
        message["Subject"] = email.subject
        message.set_content(email.text)
        try:
            await aiosmtplib.send(
                message,
                hostname=self._settings.smtp_host,
                port=self._settings.smtp_port,
                username=self._settings.smtp_username,
                password=self._settings.smtp_password,
                start_tls=self._settings.smtp_starttls,
                timeout=SMTP_TIMEOUT_SECONDS,
            )
        except (aiosmtplib.SMTPException, OSError, TimeoutError) as e:
            raise MailDeliveryError("the mail server did not accept the message") from e


@dataclass
class FakeMailSender:
    """Records messages; `fail_next(n)` makes the next n sends fail."""

    sent: list[OutgoingEmail] = field(default_factory=lambda: [])
    _failures_left: int = field(default=0, init=False, repr=False)

    def fail_next(self, count: int = 1) -> None:
        """Make the next `count` sends raise `MailDeliveryError`."""
        self._failures_left = count

    async def send(self, email: OutgoingEmail) -> None:
        """Record the email, or fail when asked to."""
        if self._failures_left > 0:
            self._failures_left -= 1
            raise MailDeliveryError("the fake mail sender was told to fail")
        self.sent.append(email)


def get_mail_sender(request: Request) -> MailSender:
    """Dependency: the app's sender, created on first use; tests override it with the fake."""
    sender: MailSender | None = request.app.state.mail_sender
    if sender is None:
        sender = SmtpMailSender(request.app.state.settings)
        request.app.state.mail_sender = sender
    return sender


def build_link(app_base_url: str, path: str, token: str) -> str:
    """The link of an email: the token stays in the fragment, out of logs and `Referer`."""
    return f"{app_base_url.rstrip('/')}/{path}#token={token}"
