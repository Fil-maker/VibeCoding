"""Shared pieces of the TDD sandbox: git helpers, the registry, test-file rules, links, hashing.

Why it exists: `tdd_sandbox.py` would pass 500 lines with all of this inline. The registry
(`harness-sandboxes.json` in the git common dir) is also read by `.claude/hooks/sandbox_guard.py`
(which carries its own tiny reader so the hook has no imports).
"""

from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, cast

REGISTRY_NAME = "harness-sandboxes.json"
NUL = chr(0)
LOCKFILES = {"uv.lock", "pnpm-lock.yaml"}  # tools rewrite them inside a sandbox
DEP_FOLDERS = ("backend/.venv", "frontend/node_modules", ".venv")


def git(cwd: Path, *args: str) -> tuple[int, str]:
    """Run git; (exit code, stdout). 127 when git is missing."""
    exe = shutil.which("git")
    if exe is None:
        return 127, ""
    proc = subprocess.run(
        [exe, "-c", "core.quotepath=off", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    return proc.returncode, proc.stdout


def repo_root(project: Path) -> Path | None:
    """Top level of the checkout that holds `project`."""
    code, out = git(project, "rev-parse", "--show-toplevel")
    return Path(out.strip()).resolve() if code == 0 and out.strip() else None


def has_head(root: Path) -> bool:
    """True when the repository has at least one commit."""
    return git(root, "rev-parse", "--verify", "-q", "HEAD")[0] == 0


def head_sha(root: Path) -> str:
    """Full HEAD commit id."""
    return git(root, "rev-parse", "HEAD")[1].strip()


def registry_path(root: Path) -> Path:
    """Registry file inside the git common dir."""
    out = git(root, "rev-parse", "--git-common-dir")[1].strip()
    common = Path(out)
    return (common if common.is_absolute() else root / common).resolve() / REGISTRY_NAME


def load_registry(root: Path) -> dict[str, dict[str, Any]]:
    """name -> sandbox record."""
    try:
        data = cast("dict[str, Any]", json.loads(registry_path(root).read_text(encoding="utf-8")))
    except (OSError, ValueError):
        return {}
    boxes = data.get("sandboxes")
    return cast("dict[str, dict[str, Any]]", boxes) if isinstance(boxes, dict) else {}


def save_registry(root: Path, boxes: dict[str, dict[str, Any]]) -> None:
    """Write the registry."""
    path = registry_path(root)
    path.write_text(json.dumps({"sandboxes": boxes}, indent=2, ensure_ascii=False), "utf-8")


def skip_path(rel: str) -> bool:
    """Dependency folders and lock files never count as sandbox changes."""
    if rel.rsplit("/", 1)[-1] in LOCKFILES:
        return True
    return any(rel == d or rel.startswith(d + "/") for d in DEP_FOLDERS)


def changed_files(root: Path) -> tuple[list[str], list[str]]:
    """(modified or untracked not-ignored files, deleted tracked files) as POSIX paths."""
    _, mod = git(root, "ls-files", "-z", "-m", "-o", "--exclude-standard")
    _, gone = git(root, "ls-files", "-z", "-d")
    deleted = {p for p in gone.split(NUL) if p}
    present = sorted({p for p in mod.split(NUL) if p and not skip_path(p)} - deleted)
    return present, sorted(deleted)


def all_files(root: Path) -> list[str]:
    """Tracked plus untracked not-ignored files that exist on disk."""
    _, out = git(root, "ls-files", "-z", "-c", "-o", "--exclude-standard")
    return sorted(p for p in out.split("\0") if p and (root / p).is_file())


def is_test_file(rel: str) -> bool:
    """Test files: backend/app/**/test_*.py, backend/tests/**, frontend/src/**/*.test.ts(x)."""
    if rel.startswith("backend/app/"):
        return re.fullmatch(r"test_[^/]*\.py", rel.rsplit("/", 1)[-1]) is not None
    if rel.startswith("backend/tests/"):
        return True
    if rel.startswith("frontend/src/"):
        return re.search(r"\.test\.tsx?$", rel) is not None
    return False


def file_hash(path: Path) -> str | None:
    """SHA-256 of a file, None when it does not exist."""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return None


def is_link(path: Path) -> bool:
    """Symlink or Windows junction."""
    return path.is_symlink() or os.path.isjunction(path)


def make_link(target: Path, source: Path) -> str | None:
    """Link `target` to the directory `source`; returns an error text or None."""
    target.parent.mkdir(parents=True, exist_ok=True)
    if sys.platform == "win32":
        cmd = shutil.which("cmd")
        if cmd is None:
            return "cmd.exe not found"
        proc = subprocess.run(
            [cmd, "/c", "mklink", "/J", str(target), str(source)],
            capture_output=True,
            text=True,
            check=False,
        )
        return None if proc.returncode == 0 else (proc.stderr or proc.stdout).strip()
    try:
        target.symlink_to(source, target_is_directory=True)
    except OSError as exc:
        return str(exc)
    return None


def remove_links(sandbox: Path) -> None:
    """Remove the dependency links first so no deletion can follow them into the checkout."""
    for rel in DEP_FOLDERS:
        link = sandbox / rel
        if is_link(link):
            if link.is_symlink():
                link.unlink()
            else:
                link.rmdir()
