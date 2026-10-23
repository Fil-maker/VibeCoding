"""Journal guard: committed journal notes are append-only.

Mode 1 (no arguments) is a PreToolUse hook on Edit|MultiEdit|Write|NotebookEdit: it reads the
payload on stdin and blocks (exit 2) a target inside `docs/journal/` (except README.md) that
exists in HEAD. A new or uncommitted note may still be fixed before its commit. If git cannot
run, existing notes are protected (fail closed).

Mode 2 (`--git-staged`) is for the pre-commit hook: it rejects (exit 1) staged deletions,
modifications and type changes of journal notes.
"""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path

MESSAGE = "committed journal notes are append-only; write a new note that links to this one"
JOURNAL = "docs/journal/"


def run_git(root: Path, *args: str) -> tuple[int, str, str]:
    """Run git; return (code, stdout, stderr). A missing git gives code 127."""
    try:
        done = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError:
        return 127, "", "git not available"
    return done.returncode, done.stdout, done.stderr


def project_dir() -> Path:
    """CLAUDE_PROJECT_DIR, else the git toplevel of the cwd, else the cwd."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    if env:
        return Path(env)
    code, out, _ = run_git(Path.cwd(), "rev-parse", "--show-toplevel")
    return Path(out.strip()) if code == 0 and out.strip() else Path.cwd()


def normalise(raw: str, root: Path) -> str:
    """Absolute, normalised, forward-slash form of a path in any Windows or POSIX spelling."""
    text = raw.replace("\\", "/")
    msys = re.match(r"^/([a-zA-Z])/(.*)", text)
    if msys:
        text = f"{msys.group(1)}:/{msys.group(2)}"
    if not (re.match(r"^[a-zA-Z]:/", text) or text.startswith("/")):
        text = f"{root.as_posix()}/{text}"
    return os.path.normpath(text).replace("\\", "/")


def relative_to_root(raw: str, root: Path) -> str | None:
    """Path of the target relative to the project, or None when it is outside."""
    target = normalise(raw, root)
    base = normalise(str(root), root).rstrip("/")
    if target.casefold().startswith(base.casefold() + "/"):
        return target[len(base) + 1 :]
    return None


def in_head(root: Path, rel: str) -> bool | None:
    """True/False whether `rel` is committed in HEAD; None when git cannot tell."""
    code, _, _ = run_git(root, "rev-parse", "--verify", "-q", "HEAD")
    if code == 1:
        return False  # no commits yet: nothing is committed
    if code != 0:
        return None
    code, _, err = run_git(root, "cat-file", "-e", f"HEAD:{rel}")
    if code == 0:
        return True
    if "does not exist" in err or "exists on disk, but not in" in err or "Not a valid" in err:
        return False
    return None


def payload_target(payload: str) -> str | None:
    """The file_path or notebook_path of a PreToolUse payload, if any."""
    try:
        data: object = json.loads(payload)
    except ValueError:
        return None
    if not isinstance(data, dict):
        return None
    tool_input: object = data.get("tool_input")  # pyright: ignore[reportUnknownMemberType]
    if not isinstance(tool_input, dict):
        return None
    raw: object = tool_input.get("file_path") or tool_input.get("notebook_path")  # pyright: ignore[reportUnknownMemberType]
    return raw if isinstance(raw, str) and raw else None


def guard_tool(payload: str) -> int:
    """Mode 1: decide for one PreToolUse payload (2 blocks, 0 allows)."""
    raw = payload_target(payload)
    root = project_dir()
    rel = relative_to_root(raw, root) if raw else None
    low = rel.casefold() if rel else ""
    if not rel or not low.startswith(JOURNAL) or low == JOURNAL + "readme.md":
        return 0
    committed = in_head(root, rel)
    if committed is None:
        committed = (root / rel).exists()  # fail closed for existing files
    if committed:
        sys.stderr.write(MESSAGE + "\n")
        return 2
    return 0


def guard_staged() -> int:
    """Mode 2: pre-commit check of the index."""
    root = project_dir()
    code, out, err = run_git(
        root, "diff", "--cached", "--name-only", "--diff-filter=DMT", "--", "docs/journal/"
    )
    if code != 0:
        sys.stderr.write(f"git failed: {err.strip()}\n")
        return 1
    bad = [p for p in out.splitlines() if p.strip() and p.strip() != "docs/journal/README.md"]
    if bad:
        sys.stderr.write(MESSAGE + ":\n" + "".join(f"  {p}\n" for p in bad))
        return 1
    return 0


def main(argv: list[str]) -> int:
    """Entry point."""
    if argv and argv[0] in {"-h", "--help"}:
        sys.stdout.write(__doc__ or "")
        return 0
    if argv and argv[0] == "--git-staged":
        return guard_staged()
    return guard_tool(sys.stdin.read())


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
