"""Raw test emails built with the standard library, the way a mail server hands them over."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime, timedelta
from email.message import EmailMessage

from app.platform.mail_reader import FolderKind

INBOX = FolderKind("inbox")
SENT = FolderKind("sent")


@dataclass(frozen=True)
class Attachment:
    """A file attached to a test email."""

    filename: str
    content: bytes = b"%PDF-1.4 test"
    maintype: str = "application"
    subtype: str = "pdf"


def raw_email(  # noqa: PLR0913 -- a mail has this many independent headers
    *,
    subject: str,
    sender: str,
    to: Sequence[str],
    sent_at: datetime,
    message_id: str | None,
    cc: Sequence[str] = (),
    in_reply_to: str | None = None,
    references: Sequence[str] = (),
    text: str | None = "Текст письма",
    html: str | None = None,
    attachments: Sequence[Attachment] = (),
) -> bytes:
    """Build one message; `text` and `html` both given make it multipart/alternative.

    `message_id`, `in_reply_to` and `references` come with angle brackets, like `<a@stroy.test>`;
    `message_id=None` leaves the `Message-ID` header out. `text=None` with `html` gives an
    HTML-only message.
    """
    message = EmailMessage()
    message["Subject"] = subject
    message["From"] = sender
    message["To"] = ", ".join(to)
    if cc:
        message["Cc"] = ", ".join(cc)
    message["Date"] = sent_at
    if message_id is not None:
        message["Message-ID"] = message_id
    if in_reply_to is not None:
        message["In-Reply-To"] = in_reply_to
    if references:
        message["References"] = " ".join(references)
    if text is not None:
        message.set_content(text)
        if html is not None:
            message.add_alternative(html, subtype="html")
    elif html is not None:
        message.set_content(html, subtype="html")
    for attachment in attachments:
        message.add_attachment(
            attachment.content,
            maintype=attachment.maintype,
            subtype=attachment.subtype,
            filename=attachment.filename,
        )
    return message.as_bytes()


def numbered_email(
    number: int,
    now: datetime,
    *,
    days_ago: float = 1.0,
    sender: str = "oleg@stroy.test",
    to: Sequence[str] = ("anna@yandex.ru",),
) -> bytes:
    """A reply-less email with its own Message-ID `<m{number}@stroy.test>`, dated `days_ago` days
    before `now`; every number gives a different email."""
    return raw_email(
        subject=f"Письмо {number}",
        sender=sender,
        to=to,
        sent_at=now - timedelta(days=days_ago),
        message_id=f"<m{number}@stroy.test>",
    )
