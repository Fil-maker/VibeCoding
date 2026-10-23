"""TDD sandbox: tests written against the spec in a copy of the repo that holds none of the code.

Why it exists: when tests and code are written in one checkout, the tests drift toward the code
they check. A git worktree outside the repo (HEAD plus the uncommitted change artifacts, no code),
with its own test database, makes the tests describe the spec. The main session runs the red check
itself and collects the tests into the checkout.

    tdd_sandbox.py <project-dir> create <name> [--base <dir>]
    tdd_sandbox.py <project-dir> red <name> [--change <c> --briefs <dir>] [--no-old]
    tdd_sandbox.py <project-dir> collect <name> [--ignore-other] [--force]
    tdd_sandbox.py <project-dir> close <name> [--also <files>...] [--change <c> --groups <n>...]
    tdd_sandbox.py <project-dir> drop <name> [--force]
    tdd_sandbox.py <project-dir> list

Exit codes: 0 ok, 1 a check failed, 2 the environment is not ready (no commits, no git).
"""

from __future__ import annotations

import argparse
import re
import shutil
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness_docs as hd
import sandbox_briefs as sb
import sandbox_common as sc
import sandbox_create as scr
import sandbox_tests as st


@dataclass
class Diff:
    """What changed in a sandbox since its snapshot."""

    new: list[str]
    changed: list[str]
    deleted: list[str]
    outside: list[str]
    old: list[str]

    @property
    def tests(self) -> list[str]:
        """New and changed test files."""
        return sorted(self.new + self.changed)


def diff_sandbox(box: dict[str, Any]) -> Diff:
    """Compare the sandbox with its snapshot."""
    path = Path(str(box["path"]))
    snap: dict[str, str | None] = box["snapshot"]
    present, gone = sc.changed_files(path)
    new: list[str] = []
    changed: list[str] = []
    old: list[str] = []
    for rel in sc.all_files(path):
        if not sc.is_test_file(rel) or sc.skip_path(rel):
            continue
        now = sc.file_hash(path / rel)
        before = snap.get(rel)
        if before is None:
            new.append(rel)
        elif before != now:
            changed.append(rel)
        else:
            old.append(rel)
    deleted = [r for r, h in snap.items() if h and sc.is_test_file(r) and not (path / r).is_file()]
    outside = [
        r for r in present if not sc.is_test_file(r) and snap.get(r, "?") != sc.file_hash(path / r)
    ]
    outside += [r for r in gone if not sc.is_test_file(r) and snap.get(r, "?") is not None]
    return Diff(new, changed, deleted, sorted(outside), old)


def need_root(project: Path) -> Path | None:
    """Repository root or None with a message."""
    root = sc.repo_root(project)
    if root is None:
        sys.stderr.write(f"{project} is not inside a git repository\n")
    return root


def get_box(root: Path, name: str) -> dict[str, Any] | None:
    """Registry record or None with a message."""
    box = sc.load_registry(root).get(name)
    if box is None or not Path(str(box["path"])).is_dir():
        sys.stderr.write(f"No sandbox {name!r} (see `list`)\n")
        return None
    return box


# --- red --------------------------------------------------------------------------------------


def cmd_red(root: Path, name: str, change: str | None, briefs: Path | None, run_old: bool) -> int:
    """`red`: run new and changed tests in the sandbox, classify, flag, write auditor briefs."""
    box = get_box(root, name)
    if box is None:
        return 2
    sandbox = Path(str(box["path"]))
    diff = diff_sandbox(box)
    out = sys.stdout.write
    if not diff.tests and not diff.deleted:
        out("No new or changed test files in the sandbox.\n")
        return 1
    report = st.run_tests(sandbox, diff.tests) if diff.tests else st.RunReport()
    labels: dict[str, str] = {}
    for rel in diff.tests:
        label, detail = st.verdict(rel, report.results)
        labels[rel] = label
        kind = "new" if rel in diff.new else "changed"
        out(f"{label:9} {rel} ({kind}): {detail}\n")
    for rel in diff.deleted:
        out(f"DELETED   {rel}: a test was deleted in the sandbox\n")
    for note in report.notes:
        out(f"NOTE: {note}\n")
    problems = len(diff.deleted) + len(report.notes)
    if diff.outside:
        out("Files outside the tests changed in the sandbox:\n")
        out("".join(f"  {f}\n" for f in diff.outside))
        problems += 1
    if run_old and diff.old:
        old_report = st.run_tests(sandbox, diff.old)
        failing = [
            f for f in diff.old if st.verdict(f, old_report.results)[0] in {"RED", "PARTIAL"}
        ]
        if failing:
            out("Old tests failing in the sandbox:\n" + "".join(f"  {f}\n" for f in failing))
            problems += 1
    all_red = bool(diff.tests) and all(v == "RED" for v in labels.values())
    out(f"\nRED check: {'ALL RED' if all_red else 'NOT all red'}; problems: {problems}\n")
    if all_red and change and briefs:
        paths = sb.write_auditor_briefs(root, sandbox, change, briefs, report.results, diff.tests)
        out("Auditor briefs:\n" + "".join(f"  {p}\n" for p in paths))
    return 0 if all_red and not problems else 1


# --- collect, close ---------------------------------------------------------------------------


def collect_tests(
    root: Path, box: dict[str, Any], ignore_other: bool, force: bool
) -> list[str] | None:
    """Copy changed test files into the checkout; None (after printing why) when refused."""
    sandbox = Path(str(box["path"]))
    snap: dict[str, str | None] = box["snapshot"]
    diff = diff_sandbox(box)
    refusals: list[str] = [f"deleted test: {r}" for r in diff.deleted]
    if diff.outside and not ignore_other:
        refusals += [f"file outside the tests: {r}" for r in diff.outside]
    todo: list[str] = []
    for rel in diff.tests:
        mine = sc.file_hash(sandbox / rel)
        theirs = sc.file_hash(root / rel)
        if theirs == mine:
            todo.append(rel)  # already collected
            continue
        if not force and theirs != snap.get(rel):
            refusals.append(f"changed in the checkout after the snapshot: {rel}")
            continue
        todo.append(rel)
    if refusals:
        sys.stdout.write("Refused:\n" + "".join(f"  {r}\n" for r in refusals))
        return None
    for rel in todo:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(sandbox / rel, target)
    return todo


def cmd_collect(root: Path, name: str, ignore_other: bool, force: bool) -> int:
    """`collect`."""
    box = get_box(root, name)
    if box is None:
        return 2
    copied = collect_tests(root, box, ignore_other, force)
    if copied is None:
        return 1
    sys.stdout.write(
        f"Collected {len(copied)} test file(s):\n" + "".join(f"  {f}\n" for f in copied)
    )
    return 0


def tick_groups(tasks: Path, groups: list[int]) -> int:
    """Tick every box of the numbered groups in tasks.md; returns how many boxes changed."""
    lines = hd.read_text(tasks).splitlines()
    inside = False
    ticked = 0
    for i, line in enumerate(lines):
        head = re.match(r"##\s+(\d+)\.", line)
        if line.startswith("## "):
            inside = head is not None and int(head.group(1)) in groups
        elif inside and re.match(r"\s*- \[ \]", line):
            lines[i] = line.replace("[ ]", "[x]", 1)
            ticked += 1
    if ticked:
        tasks.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return ticked


def cmd_close(root: Path, args: argparse.Namespace) -> int:
    """`close`: collect, run in the checkout, tick groups and drop the sandbox when green."""
    box = get_box(root, args.name)
    if box is None:
        return 2
    copied = collect_tests(root, box, args.ignore_other, args.force)
    if copied is None:
        return 1
    files = list(dict.fromkeys(copied + [f.replace("\\", "/") for f in args.also]))
    report = st.run_tests(root, files, pythonpath_backend=False)
    out = sys.stdout.write
    count = {
        k: sum(1 for r in report.results if r.outcome == k) for k in ("passed", "failed", "skipped")
    }
    out(f"{count['passed']} passed, {count['failed']} failed, {count['skipped']} skipped\n")
    for r in report.results:
        if r.outcome == "failed":
            out(f"FAILED {r.file}::{r.name}: {r.reason[:200]}\n")
    for note in report.notes:
        out(f"NOTE: {note}\n")
    green = bool(report.results) and not (count["failed"] or count["skipped"] or report.notes)
    if not green:
        out("Not green: fix the code (or the tests, per the spec) and run `close` again.\n")
        return 1
    if args.change and args.groups:
        tasks = root / "openspec" / "changes" / args.change / "tasks.md"
        out(f"Ticked {tick_groups(tasks, args.groups)} box(es) in {hd.display(root, tasks)}\n")
    scr.remove_sandbox(root, box)
    out(f"Sandbox {args.name} dropped.\n")
    return 0


# --- drop, list -------------------------------------------------------------------------------


def cmd_drop(root: Path, name: str, force: bool) -> int:
    """`drop`: refused while the sandbox holds uncollected test changes."""
    box = get_box(root, name)
    if box is None:
        return 2
    diff = diff_sandbox(box)
    uncollected = [
        r for r in diff.tests if sc.file_hash(Path(str(box["path"])) / r) != sc.file_hash(root / r)
    ]
    if (uncollected or diff.deleted) and not force:
        sys.stdout.write("Refused: uncollected test changes (use --force to drop anyway):\n")
        sys.stdout.write("".join(f"  {r}\n" for r in uncollected + diff.deleted))
        return 1
    scr.remove_sandbox(root, box)
    sys.stdout.write(f"Sandbox {name} dropped.\n")
    return 0


def cmd_list(root: Path) -> int:
    """`list`."""
    boxes = sc.load_registry(root)
    if not boxes:
        sys.stdout.write("No sandboxes.\n")
    for box in boxes.values():
        db = box.get("db") or {}
        sys.stdout.write(
            f"{box['name']}: {box['path']} (base {str(box['base'])[:8]}, created {box['created']}, "
            f"db {db.get('name', 'none')})\n"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    """CLI definition."""
    parser = argparse.ArgumentParser(description="TDD sandbox for test-writer.")
    parser.add_argument("project", type=Path, help="project directory (usually .)")
    sub = parser.add_subparsers(dest="cmd", required=True)
    create = sub.add_parser("create", help="create a sandbox and print the Sandbox block")
    create.add_argument("name")
    create.add_argument("--base", type=Path, help="parent folder for sandboxes")
    red = sub.add_parser("red", help="run new and changed tests in the sandbox and classify")
    red.add_argument("name")
    red.add_argument("--change")
    red.add_argument("--briefs", type=Path, help="folder for auditor briefs")
    red.add_argument("--no-old", action="store_true", help="skip running unchanged tests")
    collect = sub.add_parser("collect", help="copy changed tests into the checkout")
    collect.add_argument("name")
    close = sub.add_parser("close", help="collect, run in the checkout, tick groups, drop")
    close.add_argument("name")
    close.add_argument("--also", nargs="*", default=[], help="more test files to run")
    close.add_argument("--change")
    close.add_argument("--groups", nargs="*", type=int, default=[])
    for p in (collect, close):
        p.add_argument("--ignore-other", action="store_true", help="allow files outside the tests")
        p.add_argument("--force", action="store_true", help="overwrite checkout changes")
    drop = sub.add_parser("drop", help="remove a sandbox")
    drop.add_argument("name")
    drop.add_argument("--force", action="store_true")
    sub.add_parser("list", help="list sandboxes")
    return parser


def main() -> int:
    """Entry point."""
    hd.utf8_stdio()
    args = build_parser().parse_args()
    root = need_root(args.project.resolve())
    if root is None:
        return 2
    handlers = {
        "create": lambda: scr.create(root, args.name, args.base),
        "red": lambda: cmd_red(root, args.name, args.change, args.briefs, not args.no_old),
        "collect": lambda: cmd_collect(root, args.name, args.ignore_other, args.force),
        "close": lambda: cmd_close(root, args),
        "drop": lambda: cmd_drop(root, args.name, args.force),
        "list": lambda: cmd_list(root),
    }
    return handlers[args.cmd]()


if __name__ == "__main__":
    sys.exit(main())
