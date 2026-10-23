"""Storage of the decision draft (`.claude/session/facts.json`) for session_facts.py.

Kept apart so that the ADR writer and the quote checker share one model of the draft.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path

DRAFT_PATH = ".claude/session/facts.json"


@dataclass
class Decision:
    """One decision, recorded when it was made."""

    what: str
    why: str
    who: str  # "human" or "ai"
    date: str  # YYYY-MM-DD
    alternatives: str = ""
    code: str = ""
    kind: str = "technical"  # "product" or "technical"
    replaces: str = ""  # ADR id, four digits
    confirmed: bool = False
    written: str = ""  # ADR id once written


@dataclass
class Draft:
    """The whole draft of one change."""

    task: str = ""
    facts: list[str] = field(default_factory=list[str])
    keep: list[str] = field(default_factory=list[str])
    sessions: list[str] = field(default_factory=list[str])
    decisions: list[Decision] = field(default_factory=list[Decision])

    def unconfirmed(self) -> list[Decision]:
        """Decisions the user has not approved yet."""
        return [d for d in self.decisions if not d.confirmed]

    def pending_write(self) -> list[Decision]:
        """Confirmed decisions that are not in the ADRs yet."""
        return [d for d in self.decisions if d.confirmed and not d.written]


def draft_file(root: Path) -> Path:
    """Path of the draft file in a project."""
    return root / DRAFT_PATH


def _str_list(raw: object) -> list[str]:
    if not isinstance(raw, list):
        return []
    items: list[object] = list(raw)  # pyright: ignore[reportUnknownArgumentType]
    return [str(x) for x in items]


def load(root: Path) -> Draft:
    """Read the draft; an absent or unreadable file gives an empty draft."""
    path = draft_file(root)
    if not path.is_file():
        return Draft()
    try:
        raw: object = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return Draft()
    if not isinstance(raw, dict):
        return Draft()
    data: dict[str, object] = dict(raw)  # pyright: ignore[reportUnknownArgumentType]
    draft = Draft(
        task=str(data.get("task", "")),
        facts=_str_list(data.get("facts")),
        keep=_str_list(data.get("keep")),
        sessions=_str_list(data.get("sessions")),
    )
    items = data.get("decisions")
    if isinstance(items, list):
        for item in items:  # pyright: ignore[reportUnknownVariableType]
            if isinstance(item, dict):
                fields: dict[str, object] = dict(item)  # pyright: ignore[reportUnknownArgumentType]
                draft.decisions.append(_decision_from(fields))
    return draft


def _decision_from(f: dict[str, object]) -> Decision:
    return Decision(
        what=str(f.get("what", "")),
        why=str(f.get("why", "")),
        who=str(f.get("who", "ai")),
        date=str(f.get("date", "")),
        alternatives=str(f.get("alternatives", "")),
        code=str(f.get("code", "")),
        kind=str(f.get("kind", "technical")),
        replaces=str(f.get("replaces", "")),
        confirmed=bool(f.get("confirmed", False)),
        written=str(f.get("written", "")),
    )


def save(root: Path, draft: Draft) -> None:
    """Write the draft as UTF-8 JSON."""
    path = draft_file(root)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(asdict(draft), ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
