"""Commit preflight: stop a bad commit before it is made, and report what to look at.

Blocks (exit 1): a detached HEAD; a branch that is neither `main` nor `<type>/<slug>`; files
that must never be committed; a modified or deleted committed journal note; version files
changed outside a release; decisions of the draft not confirmed or not yet in the ADRs.
Reports: the journal note of this change, docs the change usually touches but did not, and
whether the database test suite is needed. Works with no commits yet.

Usage: uv run --no-project python preflight.py <project-dir> [--release]
"""

from __future__ import annotations

import argparse
import fnmatch
import importlib.util
import io
import re
import sys
from collections.abc import Callable
from pathlib import Path
from types import ModuleType
from typing import cast

DOC_SCRIPTS = Path(__file__).resolve().parents[2] / "document" / "scripts"
BRANCH_RE = re.compile(r"(feat|fix|refactor|build|ci|docs|chore|test|perf|style)/[a-z0-9][\w.-]*")
NEVER_NAMES = [".env", ".env.*", "*.pem", "*.key", "id_rsa*", "CLAUDE.local.md"]
NEVER_PREFIXES = [".claude/session/", ".claude/settings.local.json"]
NEVER_PARTS = {".cache", "__pycache__", "node_modules"}
DB_GLOBS = [
    "backend/app/**/service.py",
    "backend/app/**/repository.py",
    "backend/app/**/models.py",
    "backend/migrations/**",
    "backend/tests/integration/**",
]


def load_module(name: str) -> ModuleType:
    """Import a sibling script of the document skill by path."""
    sys.path.insert(0, str(DOC_SCRIPTS))
    spec = importlib.util.spec_from_file_location(name, DOC_SCRIPTS / f"{name}.py")
    if spec is None or spec.loader is None:
        raise ImportError(name)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def is_never_commit(path: str) -> bool:
    """True for a path that must never be committed."""
    parts = path.split("/")
    name = parts[-1]
    if name == ".env.example":
        return False
    if any(path == p.rstrip("/") or path.startswith(p) for p in NEVER_PREFIXES):
        return True
    if NEVER_PARTS & set(parts):
        return True
    return any(fnmatch.fnmatchcase(name, pat) for pat in NEVER_NAMES)


class Preflight:
    """The checks, sharing the project root and the helper modules."""

    def __init__(self, root: Path, release: bool) -> None:
        self.root = root
        self.release = release
        self.plan = load_module("doc_plan")
        self.facts = load_module("facts_store")
        self.blocks: list[str] = []
        self.git = cast(Callable[..., tuple[int, str]], self.plan.git)

    def lines(self, *args: str) -> list[str]:
        """Output lines of a git command (empty on failure)."""
        code, out = self.git(self.root, *args)
        return [ln for ln in out.splitlines() if ln.strip()] if code == 0 else []

    def has_head(self) -> bool:
        """True when the repository has at least one commit."""
        return self.git(self.root, "rev-parse", "--verify", "-q", "HEAD")[0] == 0

    def check_branch(self) -> None:
        """Detached HEAD and branch naming."""
        code, out = self.git(self.root, "symbolic-ref", "-q", "--short", "HEAD")
        branch = out.strip()
        if code != 0 or not branch:
            self.blocks.append("detached HEAD: switch to a branch first")
        elif branch != "main" and not BRANCH_RE.fullmatch(branch):
            self.blocks.append(f"branch `{branch}` is neither main nor <type>/<slug>")

    def touched(self) -> list[str]:
        """Staged, unstaged and untracked paths."""
        names = self.lines("diff", "--cached", "--name-only")
        names += self.lines("diff", "--name-only")
        names += self.lines("ls-files", "--others", "--exclude-standard")
        return sorted(set(names))

    def check_never_commit(self) -> None:
        """Secrets, caches, private notes."""
        bad = [p for p in self.touched() if is_never_commit(p)]
        if bad:
            self.blocks.append("must never be committed: " + ", ".join(bad))

    def check_journal(self) -> None:
        """Committed journal notes are append-only."""
        if not self.has_head():
            return
        bad: set[str] = set()
        for extra in (["--cached"], []):
            for line in self.lines("diff", "--name-status", *extra):
                cols = line.split("\t")
                path = cols[1] if len(cols) > 1 else ""
                if cols[0][0] in "MDTR" and path.startswith("docs/journal/"):
                    bad.add(path)
        bad.discard("docs/journal/README.md")
        if bad:
            self.blocks.append("committed journal notes changed: " + ", ".join(sorted(bad)))

    def check_version_files(self) -> None:
        """The product version and the CHANGELOG move only with /release."""
        if self.release or not self.has_head():
            return
        changed = False
        for extra in (["--cached"], []):
            if re.search(
                r"^[+-]version\s*=",
                "\n".join(self.lines("diff", *extra, "-U0", "--", "pyproject.toml")),
                re.M,
            ):
                changed = True
            if self.lines("diff", *extra, "--name-only", "--", "CHANGELOG.md"):
                changed = True
        if changed:
            self.blocks.append(
                "pyproject.toml `version` or CHANGELOG.md changed outside a release (use /release)"
            )

    def check_decisions(self) -> None:
        """Every decision of the draft is confirmed and written."""
        draft = self.facts.load(self.root)
        unconfirmed = len(draft.unconfirmed())
        unwritten = len(draft.pending_write())
        if unconfirmed:
            self.blocks.append(f"{unconfirmed} decision(s) in the draft are not confirmed")
        if unwritten:
            self.blocks.append(
                f"{unwritten} confirmed decision(s) are not written (write-decisions)"
            )

    def report(self) -> list[str]:
        """The non-blocking report."""
        changes = cast(dict[str, str], self.plan.changed_files(self.root))
        notes = sorted(
            p
            for p, s in changes.items()
            if p.startswith("docs/journal/")
            and p != "docs/journal/README.md"
            and s in {"A", "?", "R"}
        )
        out = ["Journal note(s) of this change: " + (", ".join(notes) or "none yet")]
        live = [p for p, s in changes.items() if s != "D"]
        new = [p for p, s in changes.items() if s in {"A", "?", "R"}]
        expected = cast(dict[str, list[str]], self.plan.expected_docs_for(live, new))
        for target, sources in expected.items():
            doc = target.split(" «")[0]
            if doc == "docstrings" or doc in changes:
                continue
            out.append(f"Usually touched, not touched: {target} (because of {sources[0]})")
        matches = cast(Callable[[str, str], bool], self.plan.matches)
        db = [p for p in live if any(matches(p, g) for g in DB_GLOBS)]
        out.append("Database suite needed: " + (f"yes ({db[0]}...)" if db else "no"))
        return out

    def run(self) -> int:
        """Run all checks and print the result."""
        self.check_branch()
        self.check_never_commit()
        self.check_journal()
        self.check_version_files()
        self.check_decisions()
        for line in self.report():
            sys.stdout.write(line + "\n")
        if self.blocks:
            sys.stdout.write("BLOCKED:\n")
            sys.stdout.write("".join(f"- {b}\n" for b in self.blocks))
            return 1
        sys.stdout.write("Preflight OK\n")
        return 0


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Pre-commit checks and report.")
    parser.add_argument("project_dir")
    parser.add_argument("--release", action="store_true", help="allow version/CHANGELOG changes")
    args = parser.parse_args(argv)
    return Preflight(Path(args.project_dir).resolve(), args.release).run()


if __name__ == "__main__":
    sys.exit(main())
