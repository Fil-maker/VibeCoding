"""Demo mail tool: fill the GreenMail demo mailboxes with prepared Russian emails.

A dev tool outside the app (the app itself never writes to a mailbox). Run as
`uv run --no-project python scripts/demo_mail.py <command>`, usually through `just demo-mail`.

Commands:
  load     APPEND docker/greenmail/demo/*.eml into Inbox and Sent as the manifest says; unread
           ones without \\Seen; dates shifted so the newest email is yesterday. Does nothing
           when any demo Inbox is not empty. Two emails get one file attached each: 01-c01-m1
           gets смета.xlsx and 03-c01-m3 gets договор.pdf (both in the chain of the estimate).
  status   print the count and the unread count per folder for both mailboxes.
  add-new  append one new unread email to the Inbox of anna@demo.test as a reply in an
           existing chain (for the manual «Обновить» check).

Settings come from the environment or the repo-root .env: DEMO_MAIL_HOST (localhost),
DEMO_MAIL_PORT (3143), DEMO_MAIL_PASSWORD (required).
"""

import imaplib
import io
import json
import os
import re
import sys
import zipfile
from datetime import datetime, timedelta
from email import message_from_bytes, policy
from email.message import EmailMessage
from email.utils import format_datetime, formataddr, parsedate_to_datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEMO_DIR = ROOT / "docker" / "greenmail" / "demo"
MAILBOXES = ("anna@demo.test", "anna.work@demo.test")
FOLDERS = ("INBOX", "Sent")
# Demo files that carry an attachment: file name -> (attachment name, MIME type).
ATTACHED = {
    "01-c01-m1.eml": (
        "смета.xlsx",
        "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    ),
    "03-c01-m3.eml": ("договор.pdf", "application/pdf"),
}
PDF_BYTES = (
    b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\n"
    b"2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj\n"
    b"3 0 obj<</Type/Page/Parent 2 0 R/MediaBox[0 0 200 200]>>endobj\n"
    b"trailer<</Root 1 0 R>>\n%%EOF\n"
)
CRLF = b"\r\n"


def say(text: str) -> None:
    sys.stdout.write(text + "\n")


def read_settings() -> tuple[str, int, str]:
    """Host, port and password: environment first, then the repo-root .env."""
    values: dict[str, str] = {}
    env_file = ROOT / ".env"
    if env_file.is_file():
        for line in env_file.read_text(encoding="utf-8").splitlines():
            key, sep, value = line.partition("=")
            if sep and not key.strip().startswith("#"):
                values[key.strip()] = value.strip().strip("\"'")
    values.update({k: v for k, v in os.environ.items() if k.startswith("DEMO_MAIL_")})
    password = values.get("DEMO_MAIL_PASSWORD", "")
    if not password:
        sys.exit("DEMO_MAIL_PASSWORD is not set (see .env.example)")
    return (
        values.get("DEMO_MAIL_HOST", "localhost"),
        int(values.get("DEMO_MAIL_PORT", "3143")),
        password,
    )


def connect(host: str, port: int, login: str, password: str) -> imaplib.IMAP4:
    client = imaplib.IMAP4(host, port)
    client.login(login, password)
    return client


def folder_count(client: imaplib.IMAP4, folder: str) -> tuple[int, int] | None:
    """Messages and unread in a folder; None when the folder does not exist."""
    status, _ = client.select(folder, readonly=True)
    if status != "OK":
        return None
    _, total = client.search(None, "ALL")
    _, unseen = client.search(None, "UNSEEN")
    return len((total[0] or b"").split()), len((unseen[0] or b"").split())


def normalize(raw: bytes) -> bytes:
    """CRLF line ends, as IMAP wants (the repo keeps LF)."""
    return raw.replace(CRLF, b"\n").replace(b"\n", CRLF)


def attachment_content(name: str) -> bytes:
    """The bytes of a demo attachment: a tiny PDF, or a tiny zip (an xlsx is a zip)."""
    if name.endswith(".pdf"):
        return PDF_BYTES
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w") as archive:
        archive.writestr("[Content_Types].xml", '<?xml version="1.0"?><Types/>')
    return out.getvalue()


def with_attachment(raw: bytes, name: str, mime: str) -> bytes:
    """The message with one file attached."""
    message = message_from_bytes(raw, policy=policy.default)
    assert isinstance(message, EmailMessage)
    main, _, sub_type = mime.partition("/")
    message.add_attachment(attachment_content(name), maintype=main, subtype=sub_type, filename=name)
    return normalize(message.as_bytes())


def message_date(raw: bytes) -> datetime:
    value = message_from_bytes(raw)["Date"]
    return parsedate_to_datetime(str(value))


def with_date(raw: bytes, moment: datetime) -> bytes:
    """Replace the Date header of a message."""
    header = f"Date: {format_datetime(moment)}".encode()
    return re.sub(rb"^Date:[^\r\n]*(\r\n[ \t][^\r\n]*)*", header, raw, count=1, flags=re.MULTILINE)


def append(client: imaplib.IMAP4, folder: str, raw: bytes, moment: datetime, seen: bool) -> None:
    status, _ = client.append(folder, "(\\Seen)" if seen else "", moment, raw)  # pyright: ignore[reportArgumentType]  # imaplib stubs reject None/aware date; "" and datetime are valid at runtime
    if status != "OK":
        sys.exit(f"APPEND to {folder} failed")


def ensure_sent(client: imaplib.IMAP4) -> None:
    if folder_count(client, "Sent") is None:
        client.create("Sent")


def load() -> None:
    host, port, password = read_settings()
    clients = {login: connect(host, port, login, password) for login in MAILBOXES}
    try:
        for login, client in clients.items():
            counts = folder_count(client, "INBOX")
            if counts and counts[0] > 0:
                say(f"{login}: Inbox is not empty, nothing loaded")
                return
        manifest: list[dict[str, object]] = json.loads(
            (DEMO_DIR / "manifest.json").read_text(encoding="utf-8")
        )
        raws = {
            name: normalize((DEMO_DIR / name).read_bytes())
            for name in {str(e["file"]) for e in manifest}
        }
        for name, (file_name, mime) in ATTACHED.items():
            raws[name] = with_attachment(raws[name], file_name, mime)
        newest = max(message_date(raw) for raw in raws.values())
        yesterday = datetime.now(newest.tzinfo).date() - timedelta(days=1)
        shift = (
            newest.replace(year=yesterday.year, month=yesterday.month, day=yesterday.day) - newest
        )
        for client in clients.values():
            ensure_sent(client)
        entries = sorted(manifest, key=lambda e: message_date(raws[str(e["file"])]))
        for entry in entries:
            raw = raws[str(entry["file"])]
            moment = message_date(raw) + shift
            append(
                clients[str(entry["mailbox"])],
                str(entry["folder"]),
                with_date(raw, moment),
                moment,
                bool(entry["seen"]),
            )
        say(f"loaded {len(entries)} messages into {len(MAILBOXES)} mailboxes")
    finally:
        for client in clients.values():
            client.logout()


def status() -> None:
    host, port, password = read_settings()
    for login in MAILBOXES:
        client = connect(host, port, login, password)
        try:
            for folder in FOLDERS:
                counts = folder_count(client, folder)
                shown = "missing" if counts is None else f"{counts[0]} messages, {counts[1]} unread"
                say(f"{login} {folder}: {shown}")
        finally:
            client.logout()


def add_new() -> None:
    host, port, password = read_settings()
    now = datetime.now().astimezone()
    stamp = now.strftime("%Y%m%d%H%M%S")
    sender = ("Сергей Петров", "s.petrov@stroymaster.example")
    chain = [f"<c01m{i}@demo.test>" for i in range(1, 6)]
    message = EmailMessage()
    message["From"] = formataddr(sender)
    message["To"] = formataddr(("Анна Иванова", MAILBOXES[0]))
    message["Subject"] = "Re: Смета на ремонт офиса"
    message["Date"] = format_datetime(now)
    message["Message-ID"] = f"<new{stamp}@demo.test>"
    message["In-Reply-To"] = chain[-1]
    message["References"] = " ".join(chain)
    message.set_content(
        "Анна, подтверждаю: смета зафиксирована, материалы заказаны по прежним ценам. "
        "Бригада выходит на объект в понедельник.\n\n-- \n" + sender[0] + "\n"
    )
    client = connect(host, port, MAILBOXES[0], password)
    try:
        append(client, "INBOX", normalize(message.as_bytes()), now, seen=False)
    finally:
        client.logout()
    say(f"added {message['Message-ID']} to {MAILBOXES[0]} Inbox")


COMMANDS = {"load": load, "status": status, "add-new": add_new}


def main() -> None:
    command = sys.argv[1] if len(sys.argv) > 1 else "load"
    if command not in COMMANDS:
        sys.exit(f"unknown command {command!r}; use one of: {', '.join(COMMANDS)}")
    COMMANDS[command]()


if __name__ == "__main__":
    main()
