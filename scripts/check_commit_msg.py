"""Commit-msg hook: enforce Conventional Commits.

Why: releases are computed from commit subjects (``next_version.py``), so every subject must
be ``type(scope)!: summary``. Allowed types: feat, fix, refactor, build, ci, docs, chore,
test, perf, style, revert. The first line is at most 72 characters. Auto-generated ``Merge``
and ``Revert`` messages pass. Usage: ``check_commit_msg.py <message-file>`` (exit 1 on a bad
message).
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from typing import Any, cast

TYPES = "feat|fix|refactor|build|ci|docs|chore|test|perf|style|revert"
SUBJECT_RE = re.compile(rf"^({TYPES})(\([a-z0-9][a-z0-9._/-]*\))?!?: \S.*$")
MAX_LEN = 72
AUTO_PREFIXES = ("Merge ", 'Revert "', "fixup! ", "squash! ")


def first_line(text: str) -> str:
    """The first line that is not a git comment."""
    for line in text.splitlines():
        if not line.startswith("#"):
            return line.rstrip()
    return ""


def problem(subject: str) -> str | None:
    """Why the subject is not acceptable, or None."""
    if subject.startswith(AUTO_PREFIXES):
        return None
    if not SUBJECT_RE.match(subject):
        return f"expected 'type(scope)!: summary' with type one of {TYPES.replace('|', ', ')}"
    if len(subject) > MAX_LEN:
        return f"the first line is {len(subject)} characters; the limit is {MAX_LEN}"
    return None


def main() -> int:
    """Entry point."""
    cast("Any", sys.stdout).reconfigure(encoding="utf-8")
    ap = argparse.ArgumentParser(description="Check a commit message file.")
    ap.add_argument("message_file", type=Path)
    args = ap.parse_args()
    subject = first_line(args.message_file.read_text(encoding="utf-8"))
    why = problem(subject)
    if why:
        sys.stdout.write(f"Rejected commit message {subject!r}: {why}\n")
        sys.stdout.write("Example: feat(auth): add the login page\n")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
