"""Check a new journal note before its commit.

Why: journal notes are append-only once committed, so mistakes must be caught while the note
is still new. Checks: the file name (``YYYY-MM-DD-NN-<slug>.md``, NN the next number of that
date), the header, the required sections in order, the index row appended at the end of
``docs/journal/README.md`` (earlier rows unchanged versus HEAD), relative links, quotes found
in no source, and the decisions table equal to the decision draft's ``journal-table``.
Exit 1 on any failure, 2 when the note cannot be read.
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

LOG = logging.getLogger("check_journal")
NAME_RE = re.compile(r"^(\d{4}-\d{2}-\d{2})-(\d{2})-([a-z0-9]+(?:-[a-z0-9]+)*)\.md$")
HEADER_RE = re.compile(r"^Date: \d{2}\.\d{2}\.\d{4} · Task: .+ · Change: .+$")
SECTIONS = [
    "Goal",
    "What was done",
    "Key questions to the AI",
    "Decisions",
    "Mistakes and lessons",
    "What remains",
]
LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
FACTS_SCRIPT = ".claude/skills/document/scripts/session_facts.py"


def check_name(note: Path) -> list[str]:
    """File name format and the next-number rule."""
    m = NAME_RE.match(note.name)
    if not m:
        return [f"file name {note.name!r} is not YYYY-MM-DD-NN-<slug>.md"]
    day, nn = m.group(1), int(m.group(2))
    others = [
        int(o.group(2))
        for p in note.parent.glob(f"{day}-*.md")
        if p.name != note.name and (o := NAME_RE.match(p.name))
    ]
    want = max(others, default=0) + 1
    if nn != want:
        return [f"number {nn:02d} in the file name; the next number for {day} is {want:02d}"]
    return []


def check_structure(lines: list[str]) -> list[str]:
    """Title, header line and the required sections in order."""
    errors: list[str] = []
    if not lines or not re.match(r"^# \S", lines[0]):
        errors.append("first line must be '# Title'")
    nonblank = [ln for ln in lines[1:] if ln.strip()]
    if not nonblank or not HEADER_RE.match(nonblank[0]):
        errors.append("second block must be 'Date: DD.MM.YYYY · Task: … · Change: …'")
    found = [ln[3:].strip() for ln in lines if ln.startswith("## ")]
    if found != SECTIONS:
        errors.append(f"sections must be {SECTIONS} in order; found {found}")
    return errors


def table_rows(text: str) -> list[str]:
    """Data rows of the first table of a markdown text."""
    rows = [ln.rstrip() for ln in text.splitlines() if ln.startswith("|")]
    return rows[2:]


def git_show(project: Path, spec: str) -> str | None:
    """Content of a path at HEAD, or None when HEAD or the path does not exist."""
    res = subprocess.run(
        ["git", "-C", str(project), "show", spec],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return res.stdout if res.returncode == 0 else None


def check_index(project: Path, note: Path) -> list[str]:
    """The index row is the last row; earlier rows equal HEAD's."""
    readme = project / "docs/journal/README.md"
    if not readme.is_file():
        return ["docs/journal/README.md not found"]
    text = readme.read_text("utf-8")
    rows = table_rows(text)
    errors: list[str] = []
    hits = [i for i, r in enumerate(rows) if note.name in r]
    if len(hits) != 1:
        errors.append(f"index must hold exactly one row linking {note.name}; found {len(hits)}")
    elif hits[0] != len(rows) - 1:
        errors.append("the index row must be appended at the end of the table")
    head = git_show(project, "HEAD:docs/journal/README.md")
    if head is not None:
        old = table_rows(head)
        if rows[: len(old)] != old:
            errors.append("rows before the new one differ from HEAD (the index is append-only)")
    return errors


def check_links(note: Path, text: str) -> list[str]:
    """Relative links must resolve."""
    errors: list[str] = []
    for target in LINK_RE.findall(text):
        if re.match(r"^([a-z][a-z0-9+.-]*:|#)", target, re.IGNORECASE):
            continue
        path = target.split("#", 1)[0]
        if path and not (note.parent / path).exists():
            errors.append(f"broken link: {target}")
    return errors


def run_facts(project: Path, *args: str) -> subprocess.CompletedProcess[str]:
    """Run session_facts.py through uv."""
    return subprocess.run(
        ["uv", "run", "--no-project", "python", FACTS_SCRIPT, str(project), *args],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )


def norm(rows: list[str]) -> list[str]:
    """Rows with whitespace collapsed."""
    return [re.sub(r"\s+", " ", r).strip() for r in rows if r.strip()]


def decisions_table(text: str) -> list[str]:
    """Table lines of the Decisions section."""
    m = re.search(r"^## Decisions\s*\n(.*?)(?=^## |\Z)", text, re.DOTALL | re.MULTILINE)
    return [ln for ln in (m.group(1) if m else "").splitlines() if ln.startswith("|")]


def check_facts(project: Path, note: Path, text: str) -> tuple[list[str], list[str]]:
    """Quote check and decisions-table check; returns (errors, notes)."""
    if not (project / FACTS_SCRIPT).is_file():
        return [], ["quote check skipped: decision draft script not found"]
    errors: list[str] = []
    quotes = run_facts(project, "check-quotes", str(note))
    out = quotes.stdout.strip()
    if quotes.returncode != 0 or (out and not re.match(r"(?i)^(ok|none|no |all )", out)):
        errors.append(f"quotes found in no source:\n{out or quotes.stderr.strip()}")
    table = run_facts(project, "journal-table")
    if table.returncode != 0:
        errors.append(f"journal-table failed: {table.stderr.strip() or table.stdout.strip()}")
    else:
        want = norm([ln for ln in table.stdout.splitlines() if ln.startswith("|")])
        if norm(decisions_table(text)) != want:
            errors.append("the Decisions table differs from session_facts.py journal-table")
    return errors, []


def main() -> int:
    """Entry point."""
    cast("Any", sys.stdout).reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    ap = argparse.ArgumentParser(description="Check a new journal note.")
    ap.add_argument("project_dir", type=Path)
    ap.add_argument("note_path", type=Path)
    args = ap.parse_args()
    project: Path = args.project_dir.resolve()
    note = args.note_path if args.note_path.is_absolute() else project / args.note_path
    try:
        text = note.read_text("utf-8")
    except OSError as exc:
        sys.stdout.write(f"cannot read the note: {exc}\n")
        return 2
    errors = check_name(note) + check_structure(text.splitlines())
    errors += check_index(project, note) + check_links(note, text)
    fact_errors, notes = check_facts(project, note, text)
    errors += fact_errors
    for n in notes:
        sys.stdout.write(f"NOTE {n}\n")
    for e in errors:
        sys.stdout.write(f"FAIL {e}\n")
    if errors:
        return 1
    sys.stdout.write(f"OK {note.name}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
