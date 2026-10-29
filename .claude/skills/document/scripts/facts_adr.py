"""Write confirmed decisions of the draft as ADRs and index rows (for session_facts.py).

Decisions live in `docs/adr/NNNN-<slug>.md`, indexed by `docs/decisions.md`. The reason is
copied word for word from the draft; nothing here rewrites it.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from facts_store import Decision, Draft

ADR_DIR = "docs/adr"
INDEX = "docs/decisions.md"
SECTIONS = {"product": "## Product decisions", "technical": "## Technical decisions"}
TABLE_HEAD = "| Date | ADR | Decision | Who | Status |\n| --- | --- | --- | --- | --- |"
MAX_SLUG_WORDS = 6


def who_label(d: Decision) -> str:
    """The `Who` mark of a decision as the docs write it."""
    return "[human]" if d.who == "human" else "[AI → accepted]"


def display_date(iso: str) -> str:
    """YYYY-MM-DD to DD.MM.YYYY."""
    try:
        return date.fromisoformat(iso).strftime("%d.%m.%Y")
    except ValueError:
        return iso


def make_slug(text: str) -> str:
    """ASCII slug of at most six words."""
    words = re.findall(r"[a-z0-9]+", text.lower())
    return "-".join(words[:MAX_SLUG_WORDS]) or "decision"


def next_number(adr_dir: Path) -> int:
    """Max existing ADR number plus one."""
    numbers = [
        int(m.group(1)) for p in adr_dir.glob("*.md") if (m := re.match(r"(\d{4})-", p.name))
    ]
    return max(numbers, default=0) + 1


def _escape_cell(text: str) -> str:
    return " ".join(text.replace("|", "\\|").split())


def render_adr(d: Decision, number: str, draft: Draft) -> str:
    """Render the ADR file text."""
    context = [f"Task: {draft.task or 'outside the plan'}."]
    if d.code:
        context.append(f"Code: `{d.code}`.")
    context.extend(f"- {fact}" for fact in draft.facts)
    return (
        f"# {d.what}\n\n"
        f"Id: {number} · Date: {display_date(d.date)} · Kind: {d.kind} · Status: Accepted"
        f" · Who: {who_label(d)}\n\n"
        "## Context\n" + "\n".join(context) + f"\n\n## Decision\n{d.what}\n\n"
        f"## Alternatives\n{d.alternatives or 'none recorded'}\n\n"
        f"## Reason\n{d.why}\n"
    )


def _append_index_row(text: str, d: Decision, row: str) -> str:
    heading = SECTIONS[d.kind]
    lines = text.split("\n")
    start = next((i for i, ln in enumerate(lines) if ln.strip() == heading), None)
    if start is None:
        sep = "" if text.endswith("\n\n") or not text else ("\n" if text.endswith("\n") else "\n\n")
        return f"{text}{sep}{heading}\n\n{TABLE_HEAD}\n{row}\n"
    last_row = None
    i = start + 1
    while i < len(lines) and not lines[i].startswith("## "):
        if lines[i].lstrip().startswith("|"):
            last_row = i
        i += 1
    if last_row is None:
        lines[start + 1 : start + 1] = ["", *TABLE_HEAD.split("\n"), row]
    else:
        lines.insert(last_row + 1, row)
    return "\n".join(lines)


def _supersede(root: Path, old: str, new_number: str, new_file: str) -> None:
    """Mark ADR `old` as superseded in its Status line and its index row."""
    adr_dir = root / ADR_DIR
    for path in adr_dir.glob(f"{old}-*.md"):
        text = path.read_text(encoding="utf-8")
        status = f"Superseded by [{new_number}]({new_file})"
        path.write_text(
            re.sub(r"Status: [^·\n]*?(?= ·|\n)", f"Status: {status}", text, count=1),
            encoding="utf-8",
            newline="\n",
        )
    index = root / INDEX
    if not index.is_file():
        return
    out: list[str] = []
    for line in index.read_text(encoding="utf-8").split("\n"):
        row = line.rstrip()
        if re.search(rf"\[{old}\]\(adr/{old}-", row) and row.endswith("|"):
            cells = row.removesuffix("|").rsplit("|", 1)
            out.append(f"{cells[0]}| Superseded by [{new_number}](adr/{new_file}) |")
        else:
            out.append(line)
    index.write_text("\n".join(out), encoding="utf-8", newline="\n")


def write_decisions(root: Path, draft: Draft) -> list[str]:
    """Write every confirmed, unwritten decision; return the created ADR file names."""
    adr_dir = root / ADR_DIR
    adr_dir.mkdir(parents=True, exist_ok=True)
    index = root / INDEX
    created: list[str] = []
    for d in draft.pending_write():
        number = f"{next_number(adr_dir):04d}"
        file_name = f"{number}-{make_slug(d.what)}.md"
        (adr_dir / file_name).write_text(
            render_adr(d, number, draft), encoding="utf-8", newline="\n"
        )
        row = (
            f"| {display_date(d.date)} | [{number}](adr/{file_name}) | {_escape_cell(d.what)} "
            f"| {who_label(d)} | Accepted |"
        )
        text = index.read_text(encoding="utf-8") if index.is_file() else "# Decisions\n"
        index.write_text(_append_index_row(text, d, row), encoding="utf-8", newline="\n")
        if d.replaces:
            _supersede(root, d.replaces, number, file_name)
        d.written = number
        created.append(file_name)
    return created
