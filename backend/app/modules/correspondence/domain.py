"""Pure logic of correspondence: parsing a raw message, the email key, chain choices."""

import re
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from email import message_from_bytes, policy
from email.message import EmailMessage, Message
from email.utils import getaddresses, parsedate_to_datetime
from html.parser import HTMLParser
from uuid import UUID

from app.modules.correspondence.schemas import Address

TEXT_MAX_LENGTH = 200_000
KEY_MAX_LENGTH = 998
BLOCK_TAGS = frozenset(
    {"p", "div", "br", "li", "tr", "h1", "h2", "h3", "h4", "h5", "h6", "blockquote", "pre", "table"}
)
SKIPPED_TAGS = frozenset({"script", "style", "head"})

_ANGLE_IDS = re.compile(r"<([^<>\s]+)>")
_SPACES = re.compile(r"[ \t\r\n\f\v]+")
_BLANK_LINES = re.compile(r"\n{3,}")


@dataclass(frozen=True)
class ParsedEmail:
    """What the app keeps of a raw message. Ids are normalized (see `normalize_message_id`)."""

    message_id: str | None
    in_reply_to: str | None
    references: tuple[str, ...]
    subject: str
    sender: Address
    to: tuple[Address, ...]
    cc: tuple[Address, ...]
    sent_at: datetime
    text: str
    attachment_names: tuple[str, ...]

    @property
    def related_keys(self) -> tuple[str, ...]:
        """The keys of the emails this one names, `In-Reply-To` first, without repeats."""
        named = ([self.in_reply_to] if self.in_reply_to else []) + list(self.references)
        return tuple(dict.fromkeys(named))


@dataclass(frozen=True)
class ChainRef:
    """A stored chain as chain joining sees it."""

    id: UUID
    created_at: datetime


def clean_text(value: str) -> str:
    """Drop what PostgreSQL text cannot hold: NUL characters and lone surrogates."""
    return value.replace("\x00", "").encode("utf-8", errors="replace").decode("utf-8")


def normalize_message_id(value: str | None) -> str | None:
    """A `Message-ID` without angle brackets and spaces, lower case; `None` when empty or huge."""
    if value is None:
        return None
    normalized = clean_text(value).strip().strip("<>").strip().lower()
    if not normalized or len(normalized) > KEY_MAX_LENGTH or _SPACES.search(normalized):
        return None
    return normalized


def extract_message_ids(value: str | None) -> list[str]:
    """The normalized ids of a `References`-like header, in order, without repeats."""
    if not value:
        return []
    found = _ANGLE_IDS.findall(value) or value.split()
    ids = (normalize_message_id(item) for item in found)
    return list(dict.fromkeys(item for item in ids if item is not None))


def email_key(
    parsed: ParsedEmail, *, mailbox_id: UUID, folder_id: UUID, uidvalidity: int, uid: int
) -> str:
    """The identity of an email per user: its `Message-ID`, else the place it was read from."""
    if parsed.message_id is not None:
        return parsed.message_id
    return f"no-id:{mailbox_id}:{folder_id}:{uidvalidity}:{uid}"


def choose_surviving_chain(chains: Sequence[ChainRef]) -> ChainRef:
    """The chain that absorbs the others: the oldest, ties by the smallest id."""
    return min(chains, key=lambda chain: (chain.created_at, chain.id))


class _TextExtractor(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.parts: list[str] = []
        self._skipped = 0

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in SKIPPED_TAGS:
            self._skipped += 1
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_endtag(self, tag: str) -> None:
        if tag in SKIPPED_TAGS:
            self._skipped = max(0, self._skipped - 1)
        elif tag in BLOCK_TAGS:
            self.parts.append("\n")

    def handle_data(self, data: str) -> None:
        if not self._skipped:
            self.parts.append(_SPACES.sub(" ", data))


def html_to_text(html: str) -> str:
    """Plain text of an HTML part: no markup, no `script` or `style`, entities decoded."""
    extractor = _TextExtractor()
    extractor.feed(html)
    extractor.close()
    lines = (line.strip() for line in "".join(extractor.parts).split("\n"))
    return _BLANK_LINES.sub("\n\n", "\n".join(lines)).strip()


def _part_text(part: Message) -> str:
    """The text of a part by its declared charset; undecodable bytes are replaced."""
    payload = part.get_payload(decode=True)
    if not isinstance(payload, bytes):
        return ""
    charset = part.get_content_charset() or "utf-8"
    try:
        return payload.decode(charset, errors="replace")
    except LookupError:
        return payload.decode("utf-8", errors="replace")


def _body_text(message: EmailMessage) -> str:
    plain = message.get_body(preferencelist=("plain",))
    if plain is not None:
        return _part_text(plain).replace("\r\n", "\n").replace("\r", "\n")
    html = message.get_body(preferencelist=("html",))
    return html_to_text(_part_text(html)) if html is not None else ""


def _attachment_names(message: EmailMessage) -> tuple[str, ...]:
    names = (part.get_filename() for part in message.walk() if not part.is_multipart())
    return tuple(clean_text(name) for name in names if name)


def _addresses(message: EmailMessage, header: str) -> tuple[Address, ...]:
    values = [str(value) for value in message.get_all(header, [])]
    found: dict[str, Address] = {}
    for name, address in getaddresses(values):
        lowered = clean_text(address).strip().lower()
        if lowered and lowered not in found:
            display = clean_text(name).strip()
            found[lowered] = Address(address=lowered, name=display or None)
    return tuple(found.values())


def _sent_at(message: EmailMessage, internal_date: datetime) -> datetime:
    header = message.get("Date")
    if header is not None:
        try:
            parsed = parsedate_to_datetime(str(header))
        except (ValueError, TypeError, IndexError):
            parsed = None
        if parsed is not None:
            return (parsed.replace(tzinfo=UTC) if parsed.tzinfo is None else parsed).astimezone(UTC)
    return internal_date.astimezone(UTC)


def parse_raw_message(data: bytes, internal_date: datetime) -> ParsedEmail:
    """Parse a raw message; mail is untrusted, so whatever is unreadable becomes empty."""
    message = message_from_bytes(data, policy=policy.default)
    senders = _addresses(message, "From")
    sender = senders[0] if senders else Address(address="", name=None)
    in_reply_to_ids = extract_message_ids(str(message.get("In-Reply-To") or ""))
    return ParsedEmail(
        message_id=_first(extract_message_ids(str(message.get("Message-ID") or ""))),
        in_reply_to=in_reply_to_ids[0] if in_reply_to_ids else None,
        references=tuple(extract_message_ids(str(message.get("References") or ""))),
        subject=clean_text(_SPACES.sub(" ", str(message.get("Subject") or "")).strip()),
        sender=sender,
        to=_addresses(message, "To"),
        cc=_addresses(message, "Cc"),
        sent_at=_sent_at(message, internal_date),
        text=clean_text(_body_text(message))[:TEXT_MAX_LENGTH],
        attachment_names=_attachment_names(message),
    )


def _first(items: Iterable[str]) -> str | None:
    return next(iter(items), None)


def own_address_set(addresses: Iterable[str]) -> frozenset[str]:
    """Addresses as compared: trimmed and lower case."""
    return frozenset(address.strip().lower() for address in addresses if address.strip())
