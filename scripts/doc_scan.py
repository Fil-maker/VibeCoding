"""Shared file walking for the doc checkers (check_doc_links.py, check_doc_facts.py).

Both checkers skip the same history and vendor folders and ignore fenced code blocks.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Iterator
from pathlib import Path

SKIP_DIRS = {
    ".git",
    ".venv",
    "node_modules",
    "__pycache__",
    ".cache",
    "dist",
    "coverage",
    ".ruff_cache",
    ".pytest_cache",
    ".mypy_cache",
}
SKIP_PREFIXES = ("openspec/changes/archive/", ".claude/session/")
FENCE_RE = re.compile(r"^\s*(```|~~~)")


def is_history(rel: str) -> bool:
    """Journal notes, release notes and archived changes are history, not checked."""
    if rel.startswith(SKIP_PREFIXES):
        return True
    for folder in ("docs/journal/", "docs/releases/"):
        if rel.startswith(folder) and rel != folder + "README.md":
            return True
    return False


def walk(root: Path, suffixes: set[str], names: set[str] | None = None) -> Iterator[Path]:
    """Yield project files with the given suffixes (or exact names), skipping vendor dirs."""
    for base, dirs, files in os.walk(root):
        dirs[:] = sorted(d for d in dirs if d not in SKIP_DIRS)
        for name in sorted(files):
            if Path(name).suffix in suffixes or (names and name in names):
                yield Path(base) / name


def rel_posix(root: Path, path: Path) -> str:
    """Posix path of `path` relative to `root`."""
    return path.relative_to(root).as_posix()


def read_lines(path: Path) -> list[str]:
    """Lines of a UTF-8 file; unreadable files give no lines."""
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError):
        return []


def prose_lines(lines: list[str]) -> Iterator[tuple[int, str]]:
    """Yield (line number, line) outside fenced code blocks."""
    fenced = False
    for number, line in enumerate(lines, 1):
        if FENCE_RE.match(line):
            fenced = not fenced
            continue
        if not fenced:
            yield number, line


def resolve_args(root: Path, files: list[str]) -> list[Path]:
    """Resolve file arguments (cwd-relative as a git hook passes them, or project-relative)."""
    found: list[Path] = []
    for item in files:
        path = Path(item)
        for candidate in [path] if path.is_absolute() else [Path.cwd() / path, root / path]:
            if candidate.is_file():
                resolved = candidate.resolve()
                if root in resolved.parents:
                    found.append(resolved)
                break
    return found


def setup_stdout() -> None:
    """Make stdout UTF-8 (Windows consoles default to a legacy code page)."""
    stream: object = sys.stdout
    reconfigure = getattr(stream, "reconfigure", None)
    if callable(reconfigure):
        reconfigure(encoding="utf-8")
