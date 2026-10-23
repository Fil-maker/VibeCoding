"""Change state: where every open change stopped, plus the brief files for the Code step.

Why it exists: every flow skill starts from facts injected into its prompt, and a fresh session
finds where a change stopped from files alone (artifacts, handoff markers, plan, git log).

    change_state.py <project-dir>                          print the state
    change_state.py <project-dir> brief <change> <out> [words...]
    change_state.py <project-dir> brief-spec <out> <capability> <FR-N>...

`brief` writes the change's ADDED and MODIFIED requirement blocks verbatim (all, or those whose
title has one of the words) and the design «Interface»; `brief-spec` does the same from a main
spec, for a fix without a change.
"""

from __future__ import annotations

import argparse
import logging
import re
import sys
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

import harness_docs as hd

log = logging.getLogger("change_state")


@dataclass
class ChangeInfo:
    """Facts about one open change."""

    name: str
    artifacts: list[str]
    capabilities: list[str]
    skip_specs: bool
    ticked: int
    total: int
    stage: str
    skill: str
    branch: str


def leading_skill(name: str) -> str:
    """Skill that leads a change, by its name."""
    if name.startswith("fix-"):
        return "fix"
    return "redesign" if "-redesign-" in name else "feature"


def expected_branch(name: str, skip_specs: bool) -> str:
    """Expected git branch of a change."""
    if name.startswith("fix-"):
        return f"fix/{name}"
    return f"refactor|build|chore/{name}" if skip_specs else f"feat/{name}"


def stage_of(artifacts: list[str], skip_specs: bool, markers: tuple[bool, bool]) -> str:
    """Stage: no artifacts, writing, ready, approved or code done."""
    approved, code_done = markers
    if code_done:
        return "code done"
    if approved:
        return "approved"
    core = {"proposal", "specs", "design", "tasks"} & set(artifacts)
    if not core:
        return "no artifacts"
    ready = (
        "proposal" in artifacts and "tasks" in artifacts and ("specs" in artifacts or skip_specs)
    )
    return "ready" if ready else "writing"


def inspect_change(path: Path) -> ChangeInfo:
    """Collect the facts of one change folder."""
    artifacts: list[str] = []
    for key, rel in (
        ("proposal", "proposal.md"),
        ("design", "design.md"),
        ("tasks", "tasks.md"),
        ("handoff", "handoff.md"),
    ):
        if (path / rel).is_file():
            artifacts.append(key)
    capabilities = sorted(hd.delta_files(path))
    if capabilities:
        artifacts.insert(1 if "proposal" in artifacts else 0, "specs")
    skip = hd.yaml_flag(path, "skip_specs")
    ticked, total = hd.tasks_progress(hd.read_text(path / "tasks.md"))
    markers = hd.handoff_markers(hd.read_text(path / "handoff.md"))
    return ChangeInfo(
        path.name,
        artifacts,
        capabilities,
        skip,
        ticked,
        total,
        stage_of(artifacts, skip, markers),
        leading_skill(path.name),
        expected_branch(path.name, skip),
    )


def commits_with_plan(project: Path, task_id: str) -> int:
    """Number of commits with a `Plan: <id>` footer; 0 when git has no commits yet."""
    pattern = "^Plan: " + task_id.replace(".", r"\.") + "$"
    code, out = hd.run_git(project, "log", "--format=%H", f"--grep={pattern}")
    return len(out.split()) if code == 0 else 0


def plan_status(project: Path, task_id: str, done: list[str], names: list[str]) -> str:
    """Status of a plan row: in progress, archived, done or none."""
    prefix = hd.change_prefix(task_id)
    if any(n.startswith(prefix) for n in names):
        return "in progress"
    if any(n.startswith(prefix) for n in hd.archived_changes(project)):
        return "archived"
    return "done" if task_id in done else "none"


def next_task_id(ids: list[str]) -> str:
    """Highest minor + 1 within the highest major (`0.2`)."""
    pairs = [(int(a), int(b)) for a, b in (i.split(".") for i in ids)]
    if not pairs:
        return "0.1"
    major = max(a for a, _ in pairs)
    return f"{major}.{max(b for a, b in pairs if a == major) + 1}"


def fix_handoffs(project: Path, change_names: list[str]) -> list[tuple[str, str]]:
    """Fixes without a change: (name, stage) from `.claude/session/handoff-fix-*.md`."""
    root = project / ".claude" / "session"
    found: list[tuple[str, str]] = []
    for path in sorted(root.glob("handoff-fix-*.md")) if root.is_dir() else []:
        name = path.stem.removeprefix("handoff-")
        if name in change_names:
            continue
        approved, code = hd.handoff_markers(hd.read_text(path))
        found.append((name, "code done" if code else "approved" if approved else "in progress"))
    return found


def print_state(project: Path) -> int:
    """Print the full state."""
    out = sys.stdout.write
    code, branch = hd.run_git(project, "symbolic-ref", "--short", "HEAD")
    out(f"Branch: {branch.strip() if code == 0 else '(unknown)'}\n")
    changes = [inspect_change(p) for p in hd.open_changes(project)]
    out(f"\nOpen changes: {len(changes) or 'none'}\n")
    for c in changes:
        out(f"- {c.name} [{c.skill}] stage: {c.stage}\n")
        out(f"    artifacts: {', '.join(c.artifacts) or 'none'}\n")
        out(f"    capabilities: {', '.join(c.capabilities) or 'none'}; skip_specs: ")
        out(f"{'yes' if c.skip_specs else 'no'}\n")
        out(f"    tasks: {c.ticked}/{c.total}\n    expected branch: {c.branch}\n")
    fixes = fix_handoffs(project, [c.name for c in changes])
    if fixes:
        out("\nFixes without a change:\n")
        for name, stage in fixes:
            out(f"- {name} stage: {stage}\n")
    rows, done = hd.parse_plan(project)
    out("\nPlan:\n" if rows else "\nPlan: no rows (docs/plan.md missing or empty)\n")
    names = [c.name for c in changes]
    for row in rows:
        status = plan_status(project, row.id, done, names)
        out(f"- {row.id} {row.title}: {status}, commits: {commits_with_plan(project, row.id)}\n")
    out(f"\nNext task id: {next_task_id([r.id for r in rows] + done)}\n")
    out(f"Next FR number: FR-{hd.max_fr_number(project) + 1}\n")
    return 0


# --- briefs -----------------------------------------------------------------------------------


def write_brief(
    out: Path, header: list[str], blocks: list[tuple[str, hd.Block]], iface: str
) -> None:
    """Write the brief file."""
    parts = ["# Brief", "", *header, ""]
    parts.append("## Requirements")
    for source, block in blocks:
        parts += ["", f"<!-- {source}: {block.section or 'spec'} -->", block.text]
    if iface:
        parts += ["", "## Interface", "", iface]
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(parts) + "\n", encoding="utf-8")


def cmd_brief(project: Path, change: str, out: Path, words: list[str]) -> int:
    """`brief`: requirement blocks of the change's deltas plus the design Interface."""
    folder = project / "openspec" / "changes" / change
    if not folder.is_dir():
        sys.stderr.write(f"No open change {change!r} in openspec/changes\n")
        return 2
    lowered = [w.lower() for w in words]
    blocks: list[tuple[str, hd.Block]] = []
    sources: list[str] = []
    for cap, path in hd.delta_files(folder).items():
        rel = hd.display(project, path)
        for block in hd.parse_blocks(hd.read_text(path)):
            if block.section not in {"ADDED", "MODIFIED"}:
                continue
            if lowered and not any(w in block.title.lower() for w in lowered):
                continue
            blocks.append((f"{rel} ({cap})", block))
            sources.append(rel)
    design = hd.read_text(folder / "design.md")
    iface = hd.section(design, "Interface") or ""
    header = ["Sources:", *[f"- {s}" for s in dict.fromkeys(sources)]]
    if iface:
        header.append(f"- {hd.display(project, folder / 'design.md')} (section Interface)")
    write_brief(out, header, blocks, iface)
    sys.stdout.write(f"{out}: {len(blocks)} requirement block(s), interface: ")
    sys.stdout.write("yes\n" if iface else "none\n")
    return 0 if blocks else 1


def cmd_brief_spec(project: Path, out: Path, capability: str, frs: list[str]) -> int:
    """`brief-spec`: requirement blocks of a main spec by FR number."""
    path = hd.spec_files(project).get(capability)
    if path is None:
        sys.stderr.write(f"No spec for capability {capability!r} in openspec/specs\n")
        return 2
    wanted = {int(m.group(1)) for f in frs if (m := re.search(r"(\d+)$", f))}
    blocks = [
        (hd.display(project, path), b)
        for b in hd.parse_blocks(hd.read_text(path))
        if b.fr in wanted
    ]
    missing = wanted - {b.fr for _, b in blocks}
    write_brief(out, ["Sources:", f"- {hd.display(project, path)}"], blocks, "")
    sys.stdout.write(f"{out}: {len(blocks)} requirement block(s)\n")
    for fr in sorted(missing):
        sys.stdout.write(f"not found in {capability}: FR-{fr}\n")
    return 1 if missing or not blocks else 0


def build_parser() -> argparse.ArgumentParser:
    """CLI definition."""
    parser = argparse.ArgumentParser(
        description="Print the state of the open changes or write briefs."
    )
    parser.add_argument("project", type=Path, help="project directory (usually .)")
    sub = parser.add_subparsers(dest="cmd")
    brief = sub.add_parser("brief", help="write a brief file from a change")
    brief.add_argument("change")
    brief.add_argument("out", type=Path)
    brief.add_argument("words", nargs="*", help="only requirements whose title has a word")
    spec = sub.add_parser("brief-spec", help="write a brief file from a main spec")
    spec.add_argument("out", type=Path)
    spec.add_argument("capability")
    spec.add_argument("frs", nargs="+", metavar="FR-N")
    return parser


def main() -> int:
    """Entry point."""
    hd.utf8_stdio()
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    args = build_parser().parse_args()
    project: Path = args.project.resolve()
    if args.cmd == "brief":
        return cmd_brief(project, args.change, args.out, args.words)
    if args.cmd == "brief-spec":
        return cmd_brief_spec(project, args.out, args.capability, args.frs)
    return print_state(project)


if __name__ == "__main__":
    sys.exit(main())
