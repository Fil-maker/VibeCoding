"""PreToolUse hook for the test-writer agent: keep it inside its TDD sandbox.

Why it exists: the brief says «work only in the sandbox», but a guard makes it true. It blocks
(exit 2, reason on stderr) file tools aimed at the main checkout, searches rooted in it, shell
commands that name it or start there, and commands that touch shared services (just, make, docker,
alembic, git commit/push/checkout/reset/stash). Unparseable input never blocks.

Input: the PreToolUse JSON payload on stdin (`tool_name`, `tool_input`, `cwd`).
The main checkout is $CLAUDE_PROJECT_DIR (fallback: the git top level of cwd); the sandboxes are
the paths in `harness-sandboxes.json` inside the git common dir.
"""

from __future__ import annotations

import json
import os
import re
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

FILE_TOOLS = {"Read": "file_path", "Edit": "file_path", "Write": "file_path"}
FILE_TOOLS["NotebookEdit"] = "notebook_path"
SEARCH_TOOLS = {"Grep", "Glob"}
FORBIDDEN_COMMANDS = {"just", "make", "docker", "alembic"}
FORBIDDEN_GIT = {"commit", "push", "checkout", "reset", "stash"}
WRAPPERS = {"uv", "uvx", "pnpm", "npx", "sudo", "env", "command", "time", "nohup", "exec", "xargs"}
SHELLS = {"bash", "sh", "zsh", "cmd", "powershell", "pwsh"}


def git_out(cwd: str, *args: str) -> str:
    """stdout of a git command, empty on any failure."""
    exe = shutil.which("git")
    if exe is None or not Path(cwd).is_dir():
        return ""
    try:
        proc = subprocess.run(
            [exe, *args], cwd=cwd, capture_output=True, text=True, timeout=20, check=False
        )
    except (OSError, subprocess.TimeoutExpired):
        return ""
    return proc.stdout.strip() if proc.returncode == 0 else ""


def msys_to_windows(path: str) -> str:
    """`/d/x/y` -> `d:/x/y` on Windows; other paths unchanged."""
    match = re.match(r"^/([a-zA-Z])(?:/(.*))?$", path)
    if os.name == "nt" and match:
        return f"{match.group(1)}:/{match.group(2) or ''}"
    return path


def norm(path: str, cwd: str) -> str:
    """Absolute, normalized, case-folded on Windows; relative paths resolve against cwd."""
    text = msys_to_windows(path.strip().strip("\"'"))
    full = text if Path(text).is_absolute() else str(Path(cwd) / text)
    return os.path.normcase(os.path.normpath(full))


def inside(path: str, root: str) -> bool:
    """True when the normalized `path` is `root` or below it."""
    return path == root or path.startswith(root.rstrip("\\/") + os.sep)


def sandbox_roots(main: str) -> list[str]:
    """Normalized sandbox paths from the registry."""
    common = git_out(main, "rev-parse", "--git-common-dir")
    if not common:
        return []
    registry = Path(main, common) / "harness-sandboxes.json"
    try:
        data = cast("dict[str, Any]", json.loads(registry.read_text(encoding="utf-8")))
        boxes = cast("dict[str, dict[str, Any]]", data.get("sandboxes", {}))
        return [norm(str(b["path"]), main) for b in boxes.values()]
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return []


def in_checkout(path: str, main: str, boxes: list[str]) -> bool:
    """Inside the main checkout and not inside a sandbox."""
    return inside(path, main) and not any(inside(path, b) for b in boxes)


def path_variants(main_raw: str) -> list[str]:
    """Spellings of the checkout path a command may use."""
    win = main_raw.replace("\\", "/")
    forms = {win, win.replace("/", "\\"), win.replace("/", "\\\\")}
    drive = re.match(r"^([a-zA-Z]):/(.*)$", win)
    if drive:
        forms.add(f"/{drive.group(1)}/{drive.group(2)}")
        forms.add(f"/mnt/{drive.group(1).lower()}/{drive.group(2)}")
    return sorted(forms, key=len, reverse=True)


def names_checkout(command: str, main_raw: str) -> bool:
    """True when the command names the checkout path (not a sibling like `<repo>-sandboxes`)."""
    flags = re.IGNORECASE if os.name == "nt" else 0
    for form in path_variants(main_raw.rstrip("\\/")):
        pattern = r"(?<![\w/\\.:-])" + re.escape(form) + r"(?![\w.\-])"
        if re.search(pattern, command, flags):
            return True
    return False


def leading_cd_in_sandbox(command: str, cwd: str, boxes: list[str]) -> bool:
    """True when the command starts with `cd <sandbox path>`."""
    match = re.match(r"\s*cd\s+(?:/d\s+)?(\"[^\"]+\"|'[^']+'|\S+)", command)
    if not match:
        return False
    target = norm(match.group(1), cwd)
    return any(inside(target, b) for b in boxes)


def words_of(segment: str) -> list[str]:
    """Shell words of a command segment, tolerant of Windows paths."""
    try:
        return shlex.split(segment, posix=True)
    except ValueError:
        return segment.split()


def forbidden_in(command: str) -> str | None:
    """Name of the forbidden command used by `command`, or None."""
    for segment in re.split(r"&&|\|\||[;|&\n]", command):
        words = [w for w in words_of(segment) if not re.match(r"^[A-Za-z_]\w*=", w)]
        if not words:
            continue
        name = Path(words[0].replace("\\", "/")).name.lower().removesuffix(".exe")
        rest = [Path(w.replace("\\", "/")).name.lower().removesuffix(".exe") for w in words[1:]]
        hit = reason_for(name, rest, words)
        if hit:
            return hit
    return None


def reason_for(name: str, rest: list[str], words: list[str]) -> str | None:
    """Forbidden command detection for one parsed segment."""
    if name in FORBIDDEN_COMMANDS:
        return name
    if name in WRAPPERS:
        found = next((w for w in rest if w in FORBIDDEN_COMMANDS), None)
        if found:
            return found
    if name == "git":
        args = iter(words[1:])
        for arg in args:
            if arg in {"-C", "-c", "--git-dir", "--work-tree"}:
                next(args, None)
            elif not arg.startswith("-"):
                return f"git {arg}" if arg in FORBIDDEN_GIT else None
    if name in SHELLS:
        for i, arg in enumerate(words[1:], 1):
            if arg in {"-c", "/c", "-Command", "-command"} and i + 1 < len(words):
                return forbidden_in(" ".join(words[i + 1 :]))
    return None


def check(payload: dict[str, Any]) -> str | None:
    """Reason to block, or None."""
    tool = str(payload.get("tool_name", ""))
    raw_input = payload.get("tool_input")
    tool_input = cast("dict[str, Any]", raw_input) if isinstance(raw_input, dict) else {}
    cwd = str(payload.get("cwd") or Path.cwd())
    main_raw = os.environ.get("CLAUDE_PROJECT_DIR") or git_out(cwd, "rev-parse", "--show-toplevel")
    if not main_raw:
        return None
    main = norm(main_raw, cwd)
    boxes = sandbox_roots(main_raw)
    where = norm(cwd, cwd)
    if tool in FILE_TOOLS:
        target = str(tool_input.get(FILE_TOOLS[tool]) or "")
        if target and in_checkout(norm(target, cwd), main, boxes):
            return f"{tool} on {target} is inside the main checkout. Work only in the sandbox."
    elif tool in SEARCH_TOOLS:
        target = str(tool_input.get("path") or "")
        rooted = norm(target, cwd) if target else where
        if in_checkout(rooted, main, boxes):
            return f"{tool} would search the main checkout. Pass `path` inside the sandbox."
    elif tool == "Bash":
        return check_bash(str(tool_input.get("command") or ""), cwd, main_raw, main, boxes)
    return None


def check_bash(command: str, cwd: str, main_raw: str, main: str, boxes: list[str]) -> str | None:
    """Reason to block a Bash command, or None."""
    if names_checkout(command, main_raw):
        return "The command names the main checkout. Work only in the sandbox."
    if in_checkout(norm(cwd, cwd), main, boxes) and not leading_cd_in_sandbox(command, cwd, boxes):
        return "The command runs in the main checkout. Start it with `cd <sandbox path> && ...`."
    banned = forbidden_in(command)
    if banned:
        return f"`{banned}` is not allowed for test-writer (shared services and git writes)."
    return None


def main() -> int:
    """Read the payload from stdin; exit 2 with the reason on stderr to block."""
    try:
        data: object = json.loads(sys.stdin.read())
    except ValueError:
        return 0
    if not isinstance(data, dict):
        return 0
    try:
        reason = check(cast("dict[str, Any]", data))
    except Exception as exc:
        sys.stderr.write(f"sandbox_guard: internal error ignored: {exc}\n")
        return 0
    if reason:
        sys.stderr.write(f"Blocked by sandbox_guard: {reason}\n")
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
