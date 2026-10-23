"""Task card: everything `finish` needs to check one plan task without reading whole documents.

Why it exists: acceptance is checked against the plan row, the FR texts with their scenarios, the
open boxes of the change, the «Implementation status» rows and the handoff's manual checks. This
script gathers them for a task id.

    task_card.py <project-dir> <task-id>

Exit codes: 0 ok, 1 task not found in the plan, 2 docs/plan.md is missing.
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "feature" / "scripts"))

import harness_docs as hd


def find_change(project: Path, task_id: str) -> tuple[Path | None, bool]:
    """The change of a task: (folder, is_open). Open changes win over archived ones."""
    prefix = hd.change_prefix(task_id)
    for path in hd.open_changes(project):
        if path.name.startswith(prefix):
            return path, True
    for name, path in hd.archived_changes(project).items():
        if name.startswith(prefix):
            return path, False
    return None, False


def fr_blocks(project: Path, change: Path | None, is_open: bool) -> dict[int, hd.Block]:
    """FR number -> requirement block: open deltas first, then the main specs."""
    found: dict[int, hd.Block] = {}
    sources: list[Path] = list(hd.spec_files(project).values())
    if change is not None and is_open:
        sources = list(hd.delta_files(change).values()) + sources
    for path in sources:
        for block in hd.parse_blocks(hd.read_text(path)):
            if block.fr is not None and block.fr not in found and block.section != "REMOVED":
                found[block.fr] = block
    return found


def status_rows(project: Path, task_id: str) -> list[str]:
    """Rows of `architecture.md` «Implementation status» that mention the task."""
    text = hd.read_text(project / "docs" / "architecture.md")
    rows = hd.table_rows(hd.section(text, "Implementation status") or "")
    pattern = re.compile(rf"(?<![\d.]){re.escape(task_id)}(?![\d.]*\d)")
    return [" | ".join(r) for r in rows[1:] if r and pattern.search(r[-1])]


def print_groups(change: Path) -> None:
    """Task groups of the change with the open boxes."""
    out = sys.stdout.write
    groups = hd.task_groups(hd.read_text(change / "tasks.md"))
    if not groups:
        out("(no tasks.md or no groups)\n")
    for heading, items in groups:
        ticked = sum(1 for done, _ in items if done)
        out(f"- {heading or '(no group)'}: {ticked}/{len(items)}\n")
        for done, text in items:
            if not done:
                out(f"    [ ] {text}\n")


def manual_checks(change: Path | None) -> str:
    """The `## Manual checks` section of the change's handoff."""
    if change is None:
        return ""
    return hd.section(hd.read_text(change / "handoff.md"), "Manual checks") or ""


def print_card(project: Path, task_id: str) -> int:
    """Print the card."""
    out = sys.stdout.write
    rows, _ = hd.parse_plan(project)
    if not (project / "docs" / "plan.md").is_file():
        sys.stderr.write("docs/plan.md is missing\n")
        return 2
    row = next((r for r in rows if r.id == task_id), None)
    if row is None:
        sys.stderr.write(f"Task {task_id} is not in docs/plan.md\n")
        return 1
    change, is_open = find_change(project, task_id)
    out(f"## Task {row.id}: {row.title}\nFR: {row.fr_cell}\n")
    where = "none yet" if change is None else hd.display(project, change)
    out(f"Change: {where}{'' if change is None or is_open else ' (archived)'}\n")
    out("\n## Done when\n")
    for number, item in enumerate(hd.split_items(row.done_when), 1):
        out(f"{number}. {item}\n")
    out("\n## Requirements\n")
    blocks = fr_blocks(project, change, is_open)
    for fr in row.frs:
        block = blocks.get(fr)
        out(f"\n{block.text}\n" if block else f"\nFR-{fr}: not found in specs or deltas\n")
    if not row.frs:
        out("none (FR is empty)\n")
    out("\n## Task groups\n")
    if change is None or not (change / "tasks.md").is_file():
        out("(no change or no tasks.md)\n")
    else:
        print_groups(change)
    out("\n## Implementation status\n")
    status = status_rows(project, task_id)
    out("\n".join(status) + "\n" if status else "no rows for this task\n")
    out("\n## Manual checks\n")
    checks = manual_checks(change)
    out(checks + "\n" if checks else "none recorded\n")
    return 0


def main() -> int:
    """Entry point."""
    hd.utf8_stdio()
    parser = argparse.ArgumentParser(description="Print the acceptance card of a plan task.")
    parser.add_argument("project", type=Path, help="project directory (usually .)")
    parser.add_argument("task_id", help="plan task id, for example 1.4")
    args = parser.parse_args()
    return print_card(args.project.resolve(), args.task_id)


if __name__ == "__main__":
    sys.exit(main())
