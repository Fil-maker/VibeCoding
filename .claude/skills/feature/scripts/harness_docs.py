"""Shared parsers for the harness scripts: plan, requirements, OpenSpec changes, markdown tables.

Why it exists: `change_state.py`, `task_card.py` and `tdd_sandbox.py` all read the same documents
(`docs/plan.md`, specs, change folders). One parser keeps them consistent and keeps each script
small. Standard library only; every function copes with missing files (the repo grows over time).
"""

from __future__ import annotations

import io
import re
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path

ARCHIVE = "archive"
DATE_PREFIX = re.compile(r"^\d{4}-\d{2}-\d{2}-")
FENCE = re.compile(r"^\s*(```|~~~)")


def utf8_stdio() -> None:
    """Make stdout and stderr UTF-8 (Windows consoles default to a legacy code page)."""
    for stream in (sys.stdout, sys.stderr):
        if isinstance(stream, io.TextIOWrapper):
            stream.reconfigure(encoding="utf-8")


def read_text(path: Path) -> str:
    """Read a file as UTF-8; a missing or unreadable file gives an empty string."""
    try:
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def run_git(cwd: Path, *args: str) -> tuple[int, str]:
    """Run git in `cwd`; returns (exit code, stdout). 127 when git is missing."""
    git = shutil.which("git")
    if git is None:
        return 127, ""
    try:
        proc = subprocess.run(
            [git, *args],
            cwd=cwd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError:
        return 127, ""
    return proc.returncode, proc.stdout


# --- markdown helpers -------------------------------------------------------------------------


def section(text: str, name: str, level: int = 2) -> str | None:
    """Body of the first heading of `level` whose title starts with `name` (None if absent)."""
    prefix = "#" * level + " "
    stop = re.compile(rf"^#{{1,{level}}} ")
    body: list[str] = []
    inside = False
    fenced = False
    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
        elif not fenced and stop.match(line):
            if inside:
                break
            if line.startswith(prefix) and line[len(prefix) :].strip().lower().startswith(
                name.lower()
            ):
                inside = True
            continue
        if inside:
            body.append(line)
    return "\n".join(body).strip("\n") if inside else None


def table_rows(text: str) -> list[list[str]]:
    """Rows of every markdown table in `text` (header included, separator rows dropped)."""
    rows: list[list[str]] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped.startswith("|"):
            continue
        cells = [c.strip().replace("\\|", "|") for c in re.split(r"(?<!\\)\|", stripped)[1:-1]]
        if cells and all(re.fullmatch(r":?-{2,}:?", c) for c in cells):
            continue
        rows.append(cells)
    return rows


# --- plan -------------------------------------------------------------------------------------


@dataclass(frozen=True)
class PlanRow:
    """One row of the `docs/plan.md` task table."""

    id: str
    title: str
    frs: list[int]
    fr_cell: str
    done_when: str


def split_items(cell: str) -> list[str]:
    """Split a «Done when» cell into sentences (each ends with a period)."""
    flat = re.sub(r"<br\s*/?>", " ", cell)
    parts = re.split(r"(?<=[.!?])\s+", flat.strip())
    return [p.strip() for p in parts if p.strip()]


def parse_plan(project: Path) -> tuple[list[PlanRow], list[str]]:
    """Plan rows from `## Tasks` and the ids folded into `## Done`."""
    text = read_text(project / "docs" / "plan.md")
    rows: list[PlanRow] = []
    for cells in table_rows(section(text, "Tasks") or ""):
        if len(cells) < 4 or not re.fullmatch(r"\d+\.\d+", cells[0]):
            continue
        match = re.match(r"\*\*(.+?)\*\*", cells[1])
        title = (match.group(1) if match else cells[1]).strip().rstrip(".")
        frs = [int(n) for n in re.findall(r"\d+", cells[2])]
        rows.append(PlanRow(cells[0], title, frs, cells[2], cells[3]))
    done: list[str] = []
    for line in (section(text, "Done") or "").splitlines():
        found = re.match(r"\s*[-*]\s+(\d+\.\d+)\b", line)
        if found:
            done.append(found.group(1))
    return rows, done


def change_prefix(task_id: str) -> str:
    """Change-name prefix of a plan task: `1.9` -> `1-9-`."""
    return task_id.replace(".", "-") + "-"


# --- requirements -----------------------------------------------------------------------------


@dataclass(frozen=True)
class Block:
    """A requirement block of a spec or a delta, verbatim."""

    section: str
    title: str
    fr: int | None
    text: str
    scenarios: int


def parse_blocks(text: str) -> list[Block]:
    """Requirement blocks; `section` is the first word of the `## ` heading above (ADDED…)."""
    blocks: list[Block] = []
    current = ""
    heading = ""
    lines: list[str] = []
    fenced = False

    def flush() -> None:
        if heading:
            body = "\n".join(lines).rstrip()
            fr = re.search(r"FR-(\d+)", heading)
            count = sum(1 for ln in lines if ln.startswith("#### Scenario:"))
            blocks.append(Block(current, heading, int(fr.group(1)) if fr else None, body, count))

    for line in text.splitlines():
        if FENCE.match(line):
            fenced = not fenced
        starts_heading = not fenced and re.match(r"#{1,3} ", line) is not None
        if starts_heading:
            flush()
            heading = ""
            lines = []
            if line.startswith("## "):
                words = line[3:].split()
                current = words[0].upper() if words else ""
            elif line.startswith("### Requirement:"):
                heading = line[len("### Requirement:") :].strip()
                lines = [line]
            continue
        if heading:
            lines.append(line)
    flush()
    return blocks


def spec_files(project: Path) -> dict[str, Path]:
    """Main specs: capability -> spec.md."""
    root = project / "openspec" / "specs"
    if not root.is_dir():
        return {}
    return {p.parent.name: p for p in sorted(root.glob("*/spec.md"))}


def delta_files(change_dir: Path) -> dict[str, Path]:
    """Deltas of a change: capability -> spec.md."""
    root = change_dir / "specs"
    if not root.is_dir():
        return {}
    return {p.parent.name: p for p in sorted(root.glob("*/spec.md"))}


def max_fr_number(project: Path) -> int:
    """Highest FR number over the domain header, cancelled numbers, specs and open deltas."""
    domain = read_text(project / "docs" / "domain.md")
    numbers = [int(n) for n in re.findall(r"Last FR number:\s*FR-(\d+)", domain)]
    numbers += [int(n) for n in re.findall(r"FR-(\d+)", section(domain, "Cancelled") or "")]
    files = list(spec_files(project).values())
    for change in open_changes(project):
        files += list(delta_files(change).values())
    for path in files:
        numbers += [int(n) for n in re.findall(r"Requirement:\s*FR-(\d+)", read_text(path))]
    return max(numbers, default=0)


# --- changes ----------------------------------------------------------------------------------


def open_changes(project: Path) -> list[Path]:
    """Folders of the open changes (everything under openspec/changes except `archive`)."""
    root = project / "openspec" / "changes"
    if not root.is_dir():
        return []
    return sorted(p for p in root.iterdir() if p.is_dir() and p.name != ARCHIVE)


def archived_changes(project: Path) -> dict[str, Path]:
    """Archived changes: change name (date prefix stripped) -> folder."""
    root = project / "openspec" / "changes" / ARCHIVE
    if not root.is_dir():
        return {}
    return {DATE_PREFIX.sub("", p.name): p for p in sorted(root.iterdir()) if p.is_dir()}


def yaml_flag(change_dir: Path, key: str) -> bool:
    """True when `.openspec.yaml` has `key: true`."""
    text = read_text(change_dir / ".openspec.yaml")
    return re.search(rf"^{re.escape(key)}:\s*true\b", text, re.MULTILINE) is not None


def task_groups(tasks_text: str) -> list[tuple[str, list[tuple[bool, str]]]]:
    """Groups of tasks.md: (heading, [(done, box text)])."""
    groups: list[tuple[str, list[tuple[bool, str]]]] = []
    for line in tasks_text.splitlines():
        if line.startswith("## "):
            groups.append((line[3:].strip(), []))
            continue
        box = re.match(r"\s*- \[([ xX])\]\s*(.*)", line)
        if box:
            if not groups:
                groups.append(("", []))
            groups[-1][1].append((box.group(1) != " ", box.group(2).strip()))
    return groups


def tasks_progress(tasks_text: str) -> tuple[int, int]:
    """(ticked, total) boxes of tasks.md."""
    boxes = [done for _, items in task_groups(tasks_text) for done, _ in items]
    return sum(boxes), len(boxes)


def handoff_markers(handoff_text: str) -> tuple[bool, bool]:
    """(approved, code done) from the handoff markers."""
    approved = re.search(r"^\s*-\s*Approved:\s*\d{4}-\d{2}-\d{2}", handoff_text, re.M) is not None
    code = re.search(r"^\s*-\s*Code done:\s*\d{4}-\d{2}-\d{2}", handoff_text, re.M) is not None
    return approved, code


def display(project: Path, path: Path) -> str:
    """Project-relative POSIX path for output."""
    try:
        return path.relative_to(project).as_posix()
    except ValueError:
        return path.as_posix()
