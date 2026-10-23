"""Digest of the Claude Code sessions of a change, for writing its journal note.

Why: the journal is written from what happened in every session of the change, not from
memory. The session ids come from the decision draft (``.claude/session/facts.json``) plus
``--session``. Each transcript (``~/.claude/projects/<slug>/<id>.jsonl``) is reduced to the
user's messages, the assistant's text replies, AskUserQuestion answers, edited files and the
git state. The transcript format is internal to Claude Code: unknown records are skipped.
Output longer than about 200 lines goes to a file and only its path is printed.
"""

from __future__ import annotations

import argparse
import json
import logging
import re
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any, cast

LOG = logging.getLogger("session_digest")
MAX_INLINE_LINES = 200
EDIT_TOOLS = {"Edit", "Write", "MultiEdit", "NotebookEdit"}
WRAPPER_RE = re.compile(
    r"<(system-reminder|command-name|command-message|command-args|local-command-stdout|"
    r"local-command-caveat|task-notification)\b.*?</\1>",
    re.DOTALL,
)


def as_dict(value: object) -> dict[str, Any] | None:
    """The value as a JSON object, or None."""
    return cast("dict[str, Any]", value) if isinstance(value, dict) else None


def as_list(value: object) -> list[Any]:
    """The value as a JSON array, or an empty list."""
    return cast("list[Any]", value) if isinstance(value, list) else []


def slug_of(project: Path) -> str:
    """Claude Code's folder name for a project path."""
    return re.sub(r"[^A-Za-z0-9]", "-", str(project))


def session_ids(project: Path, extra: list[str]) -> list[str]:
    """Ids from the decision draft (read defensively) plus the explicit ones."""
    ids: list[str] = []
    try:
        data = as_dict(json.loads((project / ".claude/session/facts.json").read_text("utf-8")))
        ids.extend(i for i in as_list(data.get("sessions") if data else None) if isinstance(i, str))
    except (OSError, ValueError):
        LOG.info("no readable facts.json: no session ids from the draft")
    for sid in extra:
        if sid not in ids:
            ids.append(sid)
    return ids


def find_transcript(project: Path, sid: str) -> Path | None:
    """The transcript of a session in the project's folder, else anywhere under projects."""
    base = Path.home() / ".claude" / "projects"
    direct = base / slug_of(project.resolve()) / f"{sid}.jsonl"
    if direct.is_file():
        return direct
    return next(iter(sorted(base.glob(f"*/{sid}.jsonl"))), None)


def blocks(record: dict[str, Any]) -> list[dict[str, Any]]:
    """Content blocks of a record's message, normalising plain strings."""
    msg = as_dict(record.get("message"))
    content = msg.get("content") if msg else None
    if isinstance(content, str):
        return [{"type": "text", "text": content}]
    return [d for d in (as_dict(b) for b in as_list(content)) if d is not None]


def clean(text: str) -> str:
    """Text without system-reminder and command wrappers."""
    return WRAPPER_RE.sub("", text).strip()


def result_text(block: dict[str, Any]) -> str:
    """The text of a tool_result block."""
    content = block.get("content")
    if isinstance(content, str):
        return content
    parts = [d.get("text", "") for d in (as_dict(p) for p in as_list(content)) if d]
    return "\n".join(str(p) for p in parts)


def questions_of(tool_input: object) -> list[str]:
    """Question texts of an AskUserQuestion input."""
    inp = as_dict(tool_input)
    found = (as_dict(q) for q in as_list(inp.get("questions") if inp else None))
    return [str(q["question"]) for q in found if q and "question" in q]


class Digest:
    """Facts collected from one transcript."""

    def __init__(self) -> None:
        self.users: list[str] = []
        self.replies: list[str] = []
        self.asks: list[tuple[list[str], str]] = []
        self.files: list[str] = []
        self._pending: dict[str, list[str]] = {}

    def add(self, record: dict[str, Any]) -> None:
        """Take what matters from one transcript record."""
        kind = record.get("type")
        if kind not in ("user", "assistant"):
            return
        for b in blocks(record):
            btype = b.get("type")
            if btype == "text":
                text = clean(str(b.get("text", "")))
                if text:
                    (self.users if kind == "user" else self.replies).append(text)
            elif btype == "tool_use" and kind == "assistant":
                self._tool_use(b)
            elif btype == "tool_result" and kind == "user":
                key = str(b.get("tool_use_id", ""))
                if key in self._pending:
                    self.asks.append((self._pending.pop(key), result_text(b)))

    def _tool_use(self, b: dict[str, Any]) -> None:
        name = b.get("name")
        inp = as_dict(b.get("input"))
        if name == "AskUserQuestion":
            self._pending[str(b.get("id", ""))] = questions_of(inp)
        elif name in EDIT_TOOLS and inp:
            path = inp.get("file_path") or inp.get("notebook_path")
            if isinstance(path, str) and path not in self.files:
                self.files.append(path)


def digest_transcript(path: Path) -> Digest:
    """Read a transcript, skipping lines that are not JSON objects."""
    dg = Digest()
    with path.open(encoding="utf-8", errors="replace") as fh:
        for line in fh:
            try:
                rec = as_dict(json.loads(line))
            except ValueError:
                continue
            if rec is not None:
                dg.add(rec)
    return dg


def render(sid: str, dg: Digest) -> list[str]:
    """Markdown lines of one session."""
    out = [f"## Session {sid}", "", "### User messages"]
    out += [f"- {t}" for t in dg.users] or ["- (none)"]
    out += ["", "### Assistant replies"]
    out += [f"- {t}" for t in dg.replies] or ["- (none)"]
    out += ["", "### Questions to the user"]
    for qs, answer in dg.asks:
        out.append(f"- Q: {' / '.join(qs) or '(unreadable)'}")
        out.append(f"  A: {answer.strip() or '(no answer)'}")
    if not dg.asks:
        out.append("- (none)")
    out += ["", "### Files edited"]
    out += [f"- {f}" for f in dg.files] or ["- (none)"]
    out.append("")
    return out


def git(project: Path, *args: str) -> str:
    """Output of a git command, never raising."""
    try:
        res = subprocess.run(
            ["git", "-C", str(project), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        return "(git not available)"
    return res.stdout.strip() or res.stderr.strip() or "(empty)"


def git_state(project: Path) -> list[str]:
    """Branch, short status and the last five commits."""
    return [
        "## Git state",
        f"Branch: {git(project, 'branch', '--show-current')}",
        "Status:",
        *(f"    {ln}" for ln in git(project, "status", "--short").splitlines()),
        "Last commits:",
        *(f"    {ln}" for ln in git(project, "log", "-5", "--oneline").splitlines()),
    ]


def main() -> int:
    """Entry point."""
    cast("Any", sys.stdout).reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    ap = argparse.ArgumentParser(description="Digest of the sessions of a change.")
    ap.add_argument("project_dir", type=Path)
    ap.add_argument("--session", action="append", default=[], help="extra session id")
    ap.add_argument("--out", type=Path, help="file for long output")
    args = ap.parse_args()
    project: Path = args.project_dir.resolve()
    ids = session_ids(project, args.session)
    lines = [f"# Session digest {date.today().isoformat()}", ""]
    if not ids:
        lines.append("No session ids: the decision draft lists none and --session was not given.")
    for sid in ids:
        tr = find_transcript(project, sid)
        if tr is None:
            lines += [f"## Session {sid}", "", "Transcript not found.", ""]
            continue
        lines += render(sid, digest_transcript(tr))
    lines += git_state(project)
    if len(lines) <= MAX_INLINE_LINES:
        sys.stdout.write("\n".join(lines) + "\n")
        return 0
    out: Path = args.out or project / ".claude/session" / f"digest-{date.today().isoformat()}.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    sys.stdout.write(f"Digest of {len(ids)} session(s), {len(lines)} lines: {out}\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
