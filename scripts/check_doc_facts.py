"""Doc facts checker: what the docs name must exist.

Docs drift from the repository: a renamed file, a removed recipe, a hook that is gone. This
checks that in `docs/**`, `README.md`, `CLAUDE.md` (and files given as arguments) every
repository path in backticks exists, every `just <recipe>` exists in the justfile, and every
pre-commit hook named as hook `<id>` exists in `.pre-commit-config.yaml`. A line that says
`planned` or `(task ` is exempt from the path and recipe checks. It also flags words mixing
Latin and Cyrillic letters (look-alike characters) in docs, `.claude/**/*.md` and code.
Journal notes, release notes and archived changes are history and skipped.

Usage: uv run --no-project python scripts/check_doc_facts.py <project-dir> [files...]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from doc_scan import (
    SKIP_DIRS,
    is_history,
    prose_lines,
    read_lines,
    rel_posix,
    resolve_args,
    setup_stdout,
    walk,
)

KNOWN_EXT = {
    ".py", ".md", ".ts", ".tsx", ".js", ".json", ".toml", ".yaml", ".yml", ".sql", ".sh",
    ".css", ".html", ".lock", ".ini", ".cfg", ".example", ".env", ".txt",
}  # fmt: skip
TOP_DIRS = {"backend", "frontend", "docs", "scripts", "openspec", ".claude", ".github"}
LOCAL_ONLY = (
    ".env", ".venv", "node_modules", "dist", ".cache", ".claude/session", ".claude/worktrees",
    "__pycache__", "coverage", ".claude/settings.local.json", "CLAUDE.local.md", ".ruff_cache",
    "build",
)  # fmt: skip
# Docs that describe future work by design: no existence checks (look-alikes still checked).
FUTURE_DOCS = {"docs/plan.md", "docs/ideas.md"}
SPAN_RE = re.compile(r"`([^`\n]+)`")
JUST_RE = re.compile(r"`just\s+([^\s`]+)[^`]*`")
HOOK_RE = re.compile(r"hook\s+`([\w.-]+)`")
MIXED_RE = re.compile(r"[^\W\d_]+")
EXEMPT_RE = re.compile(r"planned|\(task ", re.I)
CODE_SUFFIXES = {".py", ".ts", ".tsx"}


def justfile_recipes(root: Path) -> set[str] | None:
    """Recipe and alias names of the justfile; None when there is no justfile."""
    lines = read_lines(root / "justfile")
    if not (root / "justfile").is_file():
        return None
    names: set[str] = set()
    for line in lines:
        if not line or line[0] in " \t#[" or ":" not in line:
            continue
        alias = re.match(r"alias\s+([\w-]+)\s*:=", line)
        if alias:
            names.add(alias.group(1))
        elif not re.match(r"(set|export|import|mod)\b|[\w-]+\s*:=", line):
            names.add(line.split()[0].lstrip("@").split(":")[0])
    return names


def hook_ids(root: Path) -> set[str] | None:
    """Hook ids of .pre-commit-config.yaml; None when there is no config."""
    path = root / ".pre-commit-config.yaml"
    if not path.is_file():
        return None
    return {m.group(1) for ln in read_lines(path) if (m := re.match(r"\s*-?\s*id:\s*(\S+)", ln))}


def basenames(root: Path) -> set[str]:
    """Names of all project files, for bare file names like `settings.py`."""
    names: set[str] = set()
    for path in walk(root, KNOWN_EXT, {"justfile", "Dockerfile"}):
        names.add(path.name)
    return names


def path_candidate(span: str) -> str | None:
    """Return the repository path a backtick span names, or None when it is not a path."""
    if re.search(r"[\s<>*?{}$|=,;()\[\]\"']", span) or SCHEME_RE.match(span):
        return None
    text = span.split("#", maxsplit=1)[0]
    text = re.sub(r"(::\w+|:\d+(-\d+)?)$", "", text).removeprefix("./")
    if not text or text.startswith(("/", "-", "~")) or text.endswith("."):
        return None
    last = text.rstrip("/").split("/")[-1]
    suffix = Path(last).suffix
    if "/" in text:
        first = text.split("/")[0]
        if not (text.endswith("/") or suffix or first in TOP_DIRS):
            return None
    elif suffix.lower() not in KNOWN_EXT or last.startswith("."):
        return None if not last.startswith(".env") else text
    return text


SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")


class Checker:
    """Collects `file:line: message` problems."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.problems: list[str] = []
        self.recipes = justfile_recipes(root)
        self.hooks = hook_ids(root)
        self.names = basenames(root)

    def exists(self, text: str, source: Path) -> bool:
        """True when a path exists from the root, the docs folder or the file's folder."""
        clean = text.rstrip("/")
        if clean.startswith(LOCAL_ONLY) or any(f"/{d}/" in f"/{clean}/" for d in SKIP_DIRS):
            return True
        if "/" not in clean:
            return clean in self.names or (self.root / clean).exists()
        bases = [self.root, self.root / "docs", source.parent]
        return any((b / clean).exists() for b in bases)

    def check_docs_line(self, rel: str, number: int, line: str, source: Path) -> None:
        """Paths, recipes and hook ids named on one line of a doc."""
        exempt = EXEMPT_RE.search(line) is not None
        for m in HOOK_RE.finditer(line):
            if self.hooks is None or m.group(1) not in self.hooks:
                self.problems.append(
                    f"{rel}:{number}: hook `{m.group(1)}` not in .pre-commit-config.yaml"
                )
        if exempt:
            return
        for m in JUST_RE.finditer(line):
            name = m.group(1)
            if not name.startswith("-") and (self.recipes is None or name not in self.recipes):
                self.problems.append(f"{rel}:{number}: no recipe `{name}` in the justfile")
        for m in SPAN_RE.finditer(line):
            text = path_candidate(m.group(1))
            if text and not self.exists(text, source):
                self.problems.append(f"{rel}:{number}: path `{text}` does not exist")

    def check_doc(self, path: Path) -> None:
        """Facts of a markdown doc."""
        rel = rel_posix(self.root, path)
        if is_history(rel) or rel in FUTURE_DOCS:
            return
        for number, line in prose_lines(read_lines(path)):
            self.check_docs_line(rel, number, line, path)

    def check_mixed(self, path: Path) -> None:
        """Words that mix Latin and Cyrillic letters."""
        rel = rel_posix(self.root, path)
        if rel.startswith(("openspec/changes/archive/", ".claude/session/")):
            return
        for number, line in enumerate(read_lines(path), 1):
            for m in MIXED_RE.finditer(line):
                word = m.group(0)
                if re.search(r"[A-Za-z]", word) and re.search(r"[Ѐ-ӿ]", word):
                    self.problems.append(
                        f"{rel}:{number}: mixed Latin and Cyrillic letters in «{word}»"
                    )


def doc_files(root: Path) -> list[Path]:
    """Docs checked for facts."""
    files = [p for p in walk(root / "docs", {".md"})] if (root / "docs").is_dir() else []
    files += [root / n for n in ("README.md", "CLAUDE.md") if (root / n).is_file()]
    return files


def text_files(root: Path) -> list[Path]:
    """Files checked for look-alike characters."""
    found = [
        p
        for p in walk(root, CODE_SUFFIXES | {".md"})
        if rel_posix(root, p).endswith(".py")
        or rel_posix(root, p).startswith(("docs/", ".claude/"))
        or p.parent == root
        or p.suffix in CODE_SUFFIXES
    ]
    return found


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    setup_stdout()
    parser = argparse.ArgumentParser(description="Check that what the docs name exists.")
    parser.add_argument("project_dir")
    parser.add_argument("files", nargs="*", help="check only these files")
    args = parser.parse_args(argv)
    root = Path(args.project_dir).resolve()
    given = resolve_args(root, args.files) if args.files else None
    checker = Checker(root)
    for path in given if given is not None else doc_files(root):
        if path.suffix == ".md":
            checker.check_doc(path)
    for path in given if given is not None else text_files(root):
        if path.suffix in CODE_SUFFIXES | {".md"}:
            checker.check_mixed(path)
    if checker.problems:
        sys.stdout.write("\n".join(sorted(set(checker.problems))) + "\n")
        return 1
    sys.stdout.write("Doc facts OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
