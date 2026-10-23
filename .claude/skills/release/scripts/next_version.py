"""Propose the next product version from Conventional Commits since the last tag.

Why: the version is decided by what changed, not by a guess. The current version is the one
in the root ``pyproject.toml`` (the only source of the product version). Rules: breaking
change -> major (minor below 1.0), ``feat`` -> minor, ``fix``/``perf`` -> patch, anything
else -> nothing to release. It never proposes 1.0.0 by itself; ``--version`` overrides.
"""

from __future__ import annotations

import argparse
import logging
import re
import subprocess
import sys
import tomllib
from pathlib import Path
from typing import Any, cast

LOG = logging.getLogger("next_version")
SUBJECT_RE = re.compile(r"^(?P<type>[a-z]+)(\((?P<scope>[^)]*)\))?(?P<bang>!)?: (?P<desc>.+)$")
VERSION_RE = re.compile(r"^(\d+)\.(\d+)\.(\d+)$")
TYPE_ORDER = ["feat", "fix", "perf", "refactor", "build", "ci", "docs", "chore", "test", "style"]


def git(project: Path, *args: str) -> tuple[int, str]:
    """Run git in the project; returns (exit code, stdout)."""
    res = subprocess.run(
        ["git", "-C", str(project), *args],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    return res.returncode, res.stdout


def last_tag(project: Path) -> str | None:
    """The highest ``v*`` tag, or None."""
    code, out = git(project, "tag", "--list", "v*", "--sort=-v:refname")
    tags = out.split() if code == 0 else []
    return tags[0] if tags else None


def commits_since(project: Path, tag: str | None) -> list[tuple[str, bool]]:
    """(subject, is_breaking) for each commit since the tag; empty when there are none."""
    rng = [f"{tag}..HEAD"] if tag else []
    code, out = git(project, "log", *rng, "--format=%s%x1f%b%x1e")
    if code != 0:
        return []
    result: list[tuple[str, bool]] = []
    for rec in out.split("\x1e"):
        if not rec.strip():
            continue
        subject, _, body = rec.strip().partition("\x1f")
        breaking = bool(re.search(r"^BREAKING[ -]CHANGE:", body, re.MULTILINE))
        result.append((subject.strip(), breaking))
    return result


def parse(subject: str, breaking: bool) -> tuple[str, bool]:
    """(type, breaking) of a commit subject; unknown subjects get type 'other'."""
    m = SUBJECT_RE.match(subject)
    if not m:
        return "other", breaking
    return m.group("type"), breaking or bool(m.group("bang"))


def current_version(project: Path) -> str:
    """``[project] version`` from the root pyproject.toml."""
    data = tomllib.loads((project / "pyproject.toml").read_text("utf-8"))
    return str(data["project"]["version"])


def bump(current: str, kinds: set[str], breaking: bool) -> str | None:
    """The next version, or None when nothing is releasable."""
    m = VERSION_RE.match(current)
    if m is None:
        raise ValueError(current)
    major, minor, patch = (int(x) for x in m.groups())
    if breaking:
        return f"{major + 1}.0.0" if major >= 1 else f"0.{minor + 1}.0"
    if "feat" in kinds:
        return f"{major}.{minor + 1}.0"
    if kinds & {"fix", "perf"}:
        return f"{major}.{minor}.{patch + 1}"
    return None


def print_commits(commits: list[tuple[str, bool]]) -> set[str]:
    """Print commits grouped by type; returns the set of types seen."""
    groups: dict[str, list[str]] = {}
    for subject, breaking in commits:
        kind, brk = parse(subject, breaking)
        groups.setdefault(kind, []).append(subject + ("  [BREAKING]" if brk else ""))
    for kind in [*TYPE_ORDER, *sorted(set(groups) - set(TYPE_ORDER))]:
        if kind in groups:
            sys.stdout.write(f"{kind}:\n")
            for s in groups[kind]:
                sys.stdout.write(f"  - {s}\n")
    return set(groups)


def main() -> int:
    """Entry point."""
    cast("Any", sys.stdout).reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    ap = argparse.ArgumentParser(description="Propose the next version from commits.")
    ap.add_argument("project_dir", type=Path)
    ap.add_argument("--version", help="explicit version X.Y.Z (overrides the computation)")
    args = ap.parse_args()
    project: Path = args.project_dir.resolve()
    if args.version and not VERSION_RE.match(args.version):
        sys.stdout.write(f"--version must look like X.Y.Z, got {args.version!r}\n")
        return 1
    try:
        current = current_version(project)
    except (OSError, KeyError, tomllib.TOMLDecodeError) as exc:
        sys.stdout.write(f"cannot read [project] version from pyproject.toml: {exc}\n")
        return 2
    if not VERSION_RE.match(current):
        sys.stdout.write(f"pyproject.toml version {current!r} is not X.Y.Z\n")
        return 2
    tag = last_tag(project)
    commits = commits_since(project, tag)
    sys.stdout.write(f"Current version: {current}; last tag: {tag or 'none'}\n")
    sys.stdout.write(f"Commits since {tag or 'the start'}: {len(commits)}\n")
    seen = print_commits(commits)
    breaking = any(parse(s, b)[1] for s, b in commits)
    if args.version:
        proposed: str | None = args.version
    elif tag is None:
        proposed = "0.1.0"
    else:
        proposed = bump(current, seen, breaking)
    if proposed is None:
        sys.stdout.write("Nothing to release: no feat, fix, perf or breaking commits.\n")
        return 0
    sys.stdout.write(f"Proposed version: {proposed}\n")
    if tag is None and not args.version:
        sys.stdout.write("first release: confirm with the user\n")
    sys.stdout.write("Files to bump: pyproject.toml ([project] version)\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
