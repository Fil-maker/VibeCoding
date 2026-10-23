"""Quote checker for session_facts.py: a doc may quote a reason, never invent one.

Finds every quoted string of four or more words in the given pages and reports those that
occur in no source: the decision draft, the transcripts of the recorded sessions, recent commit
subjects, the docs at HEAD and the changed files of the working tree.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

from doc_plan import changed_files, git
from facts_store import Draft

MIN_WORDS = 4
MAX_SOURCE_BYTES = 2_000_000
QUOTE_RE = re.compile(r"«([^»\n]+)»|\"([^\"\n]+)\"|“([^”\n]+)”")


def normalise(text: str) -> str:
    """Collapse whitespace and fold case."""
    return " ".join(text.split()).casefold()


def find_quotes(text: str) -> list[tuple[int, str]]:
    """Return (line number, quote) for every quote of MIN_WORDS words or more."""
    found: list[tuple[int, str]] = []
    for number, line in enumerate(text.splitlines(), 1):
        for m in QUOTE_RE.finditer(line):
            quote = next(g for g in m.groups() if g is not None)
            if len(quote.split()) >= MIN_WORDS:
                found.append((number, quote))
    return found


def _read(path: Path) -> str:
    try:
        if path.stat().st_size > MAX_SOURCE_BYTES:
            return ""
        return path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return ""


def _transcripts(sessions: list[str]) -> list[str]:
    texts: list[str] = []
    base = Path.home() / ".claude" / "projects"
    for sid in sessions:
        for path in base.glob(f"*/{sid}.jsonl"):
            raw = path.read_text(encoding="utf-8", errors="replace")
            texts.append(raw)
            # The JSON escapes of quotes and line breaks hide plain substrings; add a decoded copy.
            texts.append(raw.replace('\\"', '"').replace("\\n", " "))
    return texts


def build_sources(root: Path, draft: Draft, pages: list[str]) -> list[str]:
    """Collect the normalised source texts a quote may come from."""
    texts = [json.dumps(draft.__dict__, ensure_ascii=False, default=lambda o: o.__dict__)]
    texts.extend(draft.facts + draft.keep + draft.sessions)
    texts.extend(_transcripts(draft.sessions))
    code, out = git(root, "log", "-50", "--format=%s")
    if code == 0:
        texts.append(out)
    code, listing = git(root, "ls-tree", "-r", "--name-only", "HEAD", "--", "docs")
    head_docs = [p for p in listing.splitlines() if p.endswith(".md")] if code == 0 else []
    for page in pages:
        if page not in head_docs:
            head_docs.append(page)
    for rel in head_docs:
        code, content = git(root, "show", f"HEAD:{rel}")
        if code == 0:
            texts.append(content)
    page_set = {Path(p).as_posix() for p in pages}
    for rel, status in changed_files(root).items():
        if status != "D" and rel not in page_set:
            texts.append(_read(root / rel))
    return [normalise(t) for t in texts]


def check_quotes(root: Path, draft: Draft, pages: list[str]) -> list[str]:
    """Return `page:line: quote` for every quote found in no source."""
    rel_pages = [Path(p).as_posix() for p in pages]
    sources = build_sources(root, draft, rel_pages)
    problems: list[str] = []
    for page in rel_pages:
        path = root / page
        for number, quote in find_quotes(_read(path)):
            needle = normalise(quote)
            if not any(needle in source for source in sources):
                problems.append(f"{page}:{number}: «{quote}»")
    return problems
