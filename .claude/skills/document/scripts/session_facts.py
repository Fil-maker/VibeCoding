"""Decision draft: record each decision when it is made, in the user's words.

Reasons recalled at the end of a session are reconstructions. This script keeps the draft of
one change in `.claude/session/facts.json` (gitignored, survives /clear and compaction), feeds
the docs and the journal from it, and renders decisions as ADRs with a script, not a model.
A subagent may quote a reason, never invent one; nothing reaches the ADRs unconfirmed.

Usage: uv run --no-project python session_facts.py <project-dir> <command> [args]
"""

from __future__ import annotations

import argparse
import io
import logging
import re
import sys
from datetime import date
from pathlib import Path

from facts_adr import display_date, who_label, write_decisions
from facts_quotes import check_quotes
from facts_store import Decision, Draft, draft_file, load, save

LOG = logging.getLogger("session_facts")


def build_parser() -> argparse.ArgumentParser:
    """The command line."""
    p = argparse.ArgumentParser(description="Decision draft of the current change.")
    p.add_argument("project_dir")
    sub = p.add_subparsers(dest="command", required=True)
    sub.add_parser("status", help="machine-friendly counts for the commit preflight")
    for name in ("sheet", "decisions", "confirm", "write-decisions", "journal-table", "clear"):
        sub.add_parser(name)
    sub.add_parser("task").add_argument("id")
    sub.add_parser("fact").add_argument("text")
    sub.add_parser("keep").add_argument("text")
    sub.add_parser("session").add_argument("session_id")
    decide = sub.add_parser("decide", help="record a decision")
    decide.add_argument("--what", required=True)
    decide.add_argument("--why", required=True)
    decide.add_argument("--who", required=True, choices=["human", "ai"])
    decide.add_argument("--alternatives", default="")
    decide.add_argument("--code", default="")
    decide.add_argument("--kind", choices=["product", "technical"], default="technical")
    decide.add_argument("--replaces", default="", help="ADR id, four digits")
    drop = sub.add_parser("drop", help="remove decision n (or fact n with --fact)")
    drop.add_argument("n", type=int)
    drop.add_argument("--fact", action="store_true")
    check = sub.add_parser("check-quotes")
    check.add_argument("pages", nargs="+")
    return p


def _state(d: Decision) -> str:
    if d.written:
        return f"in ADR {d.written}"
    return "confirmed" if d.confirmed else "NOT confirmed"


def render_decisions(draft: Draft) -> str:
    """Numbered decisions for the user."""
    if not draft.decisions:
        return "No decisions recorded"
    lines: list[str] = []
    for n, d in enumerate(draft.decisions, 1):
        lines.append(f"{n}. [{d.kind}] {d.what} - {who_label(d)} ({_state(d)})")
        lines.append(f"   Reason: {d.why}")
        if d.alternatives:
            lines.append(f"   Alternatives: {d.alternatives}")
        if d.replaces:
            lines.append(f"   Replaces ADR {d.replaces}")
    return "\n".join(lines)


def render_sheet(draft: Draft) -> str:
    """The fact sheet for doc subagents."""
    lines = [f"Task: {draft.task or 'outside the plan'}"]
    lines.append("Sessions: " + (", ".join(draft.sessions) or "none recorded"))
    lines.append("Facts:")
    lines.extend(f"{n}. {f}" for n, f in enumerate(draft.facts, 1))
    lines.append("Decisions:")
    for n, d in enumerate(draft.decisions, 1):
        lines.append(f"{n}. {d.what} - {who_label(d)}, {display_date(d.date)}, {_state(d)}")
        lines.append(f"   Reason (quote only): {d.why}")
        lines.append(f"   Alternatives: {d.alternatives or 'none recorded'}")
        lines.append(f"   Code: {d.code or '-'}")
    lines.append("Stays unchanged:")
    lines.extend(f"- {k}" for k in draft.keep)
    return "\n".join(lines)


def render_journal_table(draft: Draft) -> str:
    """Rows of the journal decisions table."""

    def cell(text: str) -> str:
        return " ".join(text.replace("|", "\\|").split()) or "-"

    rows = ["| Decision | Alternatives | Reason | Who |", "| --- | --- | --- | --- |"]
    rows.extend(
        f"| {cell(d.what)} | {cell(d.alternatives)} | {cell(d.why)} | {who_label(d)} |"
        for d in draft.decisions
    )
    return "\n".join(rows)


def cmd_decide(root: Path, draft: Draft, a: argparse.Namespace) -> int:
    """Record a decision."""
    if a.replaces and not re.fullmatch(r"\d{4}", a.replaces):
        LOG.error("--replaces takes an ADR id of four digits, e.g. 0004")
        return 1
    draft.decisions.append(
        Decision(
            what=a.what,
            why=a.why,
            who=a.who,
            date=date.today().isoformat(),
            alternatives=a.alternatives,
            code=a.code,
            kind=a.kind,
            replaces=a.replaces,
        )
    )
    save(root, draft)
    sys.stdout.write(f"Recorded decision {len(draft.decisions)}\n")
    return 0


def cmd_drop(root: Path, draft: Draft, a: argparse.Namespace) -> int:
    """Remove a decision or a fact by number."""
    items: list[Decision] | list[str] = draft.facts if a.fact else draft.decisions
    if not 1 <= a.n <= len(items):
        LOG.error("no item %d", a.n)
        return 1
    if not a.fact and draft.decisions[a.n - 1].written:
        LOG.error("decision %d is already in an ADR; supersede it with a new decision", a.n)
        return 1
    del items[a.n - 1]
    save(root, draft)
    sys.stdout.write("Dropped\n")
    return 0


def cmd_write(root: Path, draft: Draft, _a: argparse.Namespace) -> int:
    """Write the confirmed decisions as ADRs."""
    if draft.unconfirmed():
        LOG.error(
            "%d decision(s) not confirmed; run `confirm` after the user approves",
            len(draft.unconfirmed()),
        )
        return 1
    created = write_decisions(root, draft)
    save(root, draft)
    sys.stdout.write("\n".join(f"docs/adr/{c}" for c in created) or "Nothing to write")
    sys.stdout.write("\n")
    return 0


def cmd_edit(root: Path, draft: Draft, a: argparse.Namespace) -> int:
    """Commands that only change the draft."""
    cmd: str = a.command
    if cmd == "confirm":
        for d in draft.decisions:
            d.confirmed = True
    elif cmd == "task":
        draft.task = a.id
    elif cmd == "fact":
        draft.facts.append(a.text)
    elif cmd == "keep":
        draft.keep.append(a.text)
    elif cmd == "session" and a.session_id not in draft.sessions:
        draft.sessions.append(a.session_id)
    save(root, draft)
    sys.stdout.write("OK\n")
    return 0


def cmd_quotes(root: Path, draft: Draft, a: argparse.Namespace) -> int:
    """Check the quotes of pages."""
    problems = check_quotes(root, draft, a.pages)
    sys.stdout.write("\n".join(problems) if problems else "All quotes have a source")
    sys.stdout.write("\n")
    return 1 if problems else 0


def cmd_clear(root: Path, _draft: Draft, _a: argparse.Namespace) -> int:
    """Delete the draft after the commit."""
    draft_file(root).unlink(missing_ok=True)
    sys.stdout.write("Cleared\n")
    return 0


def render_status(draft: Draft) -> str:
    """Counts for the commit preflight."""
    return (
        f"unconfirmed={len(draft.unconfirmed())}\n"
        f"confirmed_not_written={len(draft.pending_write())}"
    )


def run(root: Path, a: argparse.Namespace) -> int:
    """Dispatch a command."""
    draft = load(root)
    cmd: str = a.command
    text = {
        "sheet": render_sheet,
        "decisions": render_decisions,
        "journal-table": render_journal_table,
        "status": render_status,
    }
    if cmd in text:
        sys.stdout.write(text[cmd](draft) + "\n")
        return 0
    handlers = {
        "decide": cmd_decide,
        "drop": cmd_drop,
        "write-decisions": cmd_write,
        "check-quotes": cmd_quotes,
        "clear": cmd_clear,
    }
    return handlers.get(cmd, cmd_edit)(root, draft, a)


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    args = build_parser().parse_args(argv)
    return run(Path(args.project_dir).resolve(), args)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stderr, format="%(message)s")
    sys.exit(main())
