"""Doc link checker: links, anchors and section references in the docs must resolve.

Docs rot silently when a file or a heading is renamed. This checks that every relative
markdown link and `#anchor` resolves (GitHub slug rules), that every reference of the form
`<file>.md «Heading»` in docs, rules, skills, agents, configs and code comments names an
existing heading, and that headings in `docs/**` carry no section numbers. Journal and release
notes, archived changes, vendor folders and fenced code are skipped.

Usage: uv run --no-project python scripts/check_doc_links.py <project-dir> [files...]
"""

from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path
from urllib.parse import unquote

from doc_scan import (
    is_history,
    prose_lines,
    read_lines,
    rel_posix,
    resolve_args,
    setup_stdout,
    walk,
)

REF_SUFFIXES = {
    ".md",
    ".mdc",
    ".py",
    ".ts",
    ".tsx",
    ".js",
    ".yaml",
    ".yml",
    ".toml",
    ".json",
    ".sh",
}
LINK_RE = re.compile(r"(?<!\!)\[[^\]]*\]\(\s*<?([^)\s>]+)>?(?:\s+\"[^\"]*\")?\s*\)")
REFDEF_RE = re.compile(r"^\s{0,3}\[[^\]]+\]:\s*<?(\S+?)>?(?:\s|$)")
SCHEME_RE = re.compile(r"^[a-zA-Z][a-zA-Z0-9+.-]*:")
HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
NUMBERED_RE = re.compile(r"^\d+(\.\d+)*[.)]?\s")
CODE_SPAN_RE = re.compile(r"`[^`\n]*`")
REF_RE = re.compile(r"([\w./-]+\.md)`?\s*«([^»\n]+)»")


def plain_heading(text: str) -> str:
    """Heading text without inline markdown."""
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)
    return text.replace("`", "").replace("*", "").strip()


def slugify(text: str) -> str:
    """GitHub anchor of a heading: lower case, punctuation dropped, spaces to hyphens."""
    kept = re.sub(r"[^\w\- ]", "", plain_heading(text).lower())
    return kept.replace(" ", "-")


class Headings:
    """Headings of one markdown file: texts and anchors (with duplicate suffixes)."""

    def __init__(self, path: Path) -> None:
        self.texts: set[str] = set()
        self.anchors: set[str] = set()
        seen: dict[str, int] = {}
        for _, line in prose_lines(read_lines(path)):
            m = HEADING_RE.match(line)
            if not m:
                continue
            plain = plain_heading(m.group(2))
            self.texts.add(" ".join(plain.split()).casefold())
            slug = slugify(m.group(2))
            count = seen.get(slug, 0)
            seen[slug] = count + 1
            self.anchors.add(slug if count == 0 else f"{slug}-{count}")


class Checker:
    """Runs the checks and collects `file:line: broken target` problems."""

    def __init__(self, root: Path) -> None:
        self.root = root
        self.problems: list[str] = []
        self.cache: dict[Path, Headings] = {}

    def headings(self, path: Path) -> Headings:
        """Cached headings of a markdown file."""
        if path not in self.cache:
            self.cache[path] = Headings(path)
        return self.cache[path]

    def report(self, rel: str, line: int, msg: str) -> None:
        """Record a problem."""
        self.problems.append(f"{rel}:{line}: {msg}")

    def check_link(self, rel: str, number: int, source: Path, target: str) -> None:
        """Check one relative link, with its optional anchor."""
        if SCHEME_RE.match(target) or target.startswith("//"):
            return
        path_part, _, anchor = target.partition("#")
        path_part = unquote(path_part).split("?")[0]
        if path_part:
            base = self.root if path_part.startswith("/") else source.parent
            dest = (base / path_part.lstrip("/")).resolve()
            if not dest.exists():
                self.report(rel, number, f"broken link {target}")
                return
        else:
            dest = source
        known = anchor and dest.is_file() and dest.suffix == ".md"
        if known and unquote(anchor).lower() not in self.headings(dest).anchors:
            self.report(rel, number, f"broken anchor {target}")

    def check_refs(self, rel: str, number: int, source: Path, line: str) -> None:
        """Check `<file>.md «Heading»` references on one line."""
        for m in REF_RE.finditer(line):
            name, heading = m.group(1), " ".join(m.group(2).split()).casefold()
            candidates = [self.root / name, source.parent / name, self.root / "docs" / name]
            dest = next((c for c in candidates if c.is_file()), None)
            if dest is None:
                self.report(rel, number, f"{name} «{m.group(2)}»: file not found")
            elif heading not in self.headings(dest).texts:
                self.report(rel, number, f"{name} «{m.group(2)}»: no such heading")

    def check_file(self, path: Path) -> None:
        """All checks for one file."""
        rel = rel_posix(self.root, path)
        if is_history(rel):
            return
        lines = read_lines(path)
        is_md = path.suffix == ".md"
        for number, line in prose_lines(lines) if is_md else enumerate(lines, 1):
            self.check_refs(rel, number, path, line)
            if not is_md:
                continue
            stripped = CODE_SPAN_RE.sub("", line)
            targets = LINK_RE.findall(stripped)
            ref = REFDEF_RE.match(stripped)
            self.check_numbers(rel, number, line)
            for target in [*targets, *([ref.group(1)] if ref else [])]:
                self.check_link(rel, number, path, target)

    def check_numbers(self, rel: str, number: int, line: str) -> None:
        """Headings in docs carry no section numbers."""
        m = HEADING_RE.match(line)
        if m and rel.startswith("docs/") and NUMBERED_RE.match(m.group(2)):
            self.report(rel, number, f"section number in heading «{m.group(2)}»")


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    setup_stdout()
    parser = argparse.ArgumentParser(description="Check links, anchors and heading references.")
    parser.add_argument("project_dir")
    parser.add_argument("files", nargs="*", help="check only these files")
    args = parser.parse_args(argv)
    root = Path(args.project_dir).resolve()
    paths = (
        resolve_args(root, args.files)
        if args.files
        else list(walk(root, REF_SUFFIXES, {"justfile"}))
    )
    checker = Checker(root)
    for path in paths:
        checker.check_file(path)
    if checker.problems:
        sys.stdout.write("\n".join(checker.problems) + "\n")
        return 1
    sys.stdout.write("Doc links OK\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
