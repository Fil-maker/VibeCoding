"""Pure helpers of IMAP folder names: reading `LIST` lines, choosing the Sent folder."""

import base64
import binascii
import re
from dataclasses import dataclass

SENT_ATTRIBUTE = "\\sent"
NO_SELECT_ATTRIBUTE = "\\noselect"
QUOTE_LENGTH = 2
# Used when the server does not mark a folder with the `\Sent` attribute.
SENT_NAMES = ("sent", "sent items", "отправленные", "inbox.sent")

_LIST_LINE = re.compile(r'^\((?P<flags>[^)]*)\)\s+(?:"(?:[^"\\]|\\.)*"|NIL)\s+(?P<name>.+)$')
_ENCODED_RUN = re.compile(r"&([^-]*)-")
_LITERAL_MARK = re.compile(r"\s*\{\d+\}$")
_ESCAPED = re.compile(r"\\(.)")


@dataclass(frozen=True)
class FolderEntry:
    """A folder of `LIST`: its name as the server spells it (to send back) and its attributes."""

    name: str
    decoded_name: str
    attributes: frozenset[str]


def _decode_run(match: re.Match[str]) -> str:
    chunk = match.group(1)
    if not chunk:
        return "&"
    padded = chunk.replace(",", "/")
    padded += "=" * (-len(padded) % 4)
    try:
        return base64.b64decode(padded).decode("utf-16-be", errors="replace")
    except (binascii.Error, ValueError):
        return match.group(0)


def decode_mailbox_name(name: str) -> str:
    """Decode the modified UTF-7 of IMAP folder names («&BB4-» → «О»)."""
    return _ENCODED_RUN.sub(_decode_run, name)


def quote_mailbox(name: str) -> str:
    """The folder name as one quoted IMAP string."""
    escaped = name.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def _list_text(item: bytes | tuple[bytes, bytes] | None) -> str | None:
    if item is None:
        return None
    if isinstance(item, tuple):
        head, literal = item
        marker = _LITERAL_MARK.sub("", head.decode("utf-8", errors="replace"))
        return f"{marker} {quote_mailbox(literal.decode('utf-8', errors='replace'))}"
    return item.decode("utf-8", errors="replace")


def parse_list_response(items: list[bytes | tuple[bytes, bytes] | None]) -> list[FolderEntry]:
    """The folders of a `LIST` answer; lines that do not parse are skipped."""
    entries: list[FolderEntry] = []
    for item in items:
        text = _list_text(item)
        match = _LIST_LINE.match(text.strip()) if text is not None else None
        if match is None:
            continue
        name = match.group("name").strip()
        if name.startswith('"') and name.endswith('"') and len(name) >= QUOTE_LENGTH:
            name = _ESCAPED.sub(r"\1", name[1:-1])
        attributes = frozenset(flag.lower() for flag in match.group("flags").split())
        entries.append(FolderEntry(name, decode_mailbox_name(name), attributes))
    return entries


def find_sent_folder(entries: list[FolderEntry]) -> FolderEntry | None:
    """The folder with the Sent attribute, else the first existing of the well-known names."""
    selectable = [entry for entry in entries if NO_SELECT_ATTRIBUTE not in entry.attributes]
    for entry in selectable:
        if SENT_ATTRIBUTE in entry.attributes:
            return entry
    for wanted in SENT_NAMES:
        for entry in selectable:
            if entry.decoded_name.lower() == wanted:
                return entry
    return None
