"""Session start: install the tooling and dependencies in a Claude Code cloud session.

A SessionStart hook. It does nothing outside the cloud (`CLAUDE_CODE_REMOTE` is not `true`): on a
developer machine `just setup` does this once. In the cloud the container starts from a fresh
clone, so the hook brings the tools to the versions in `docs/tech.md` «Stack» (pnpm, just, prek,
openspec), installs the harness, backend and frontend dependencies, and installs the git hooks, so
`just check`, `just test` and commits work in the session. Every step is idempotent; the container
is cached after the hook, so later sessions mostly find the tools in place. Exit 1 when a step
fails.
"""

from __future__ import annotations

import os
import shutil
import subprocess
import sys
from pathlib import Path

PNPM_VERSION = "12.15.0"
JUST_VERSION = "1.59.0"
PREK_SPEC = "prek>=0.5,<0.6"
OPENSPEC_VERSION = "1.14.3"


def project_dir() -> Path:
    """CLAUDE_PROJECT_DIR, else the repository root next to this file."""
    env = os.environ.get("CLAUDE_PROJECT_DIR")
    return Path(env) if env else Path(__file__).resolve().parent.parent.parent


def tool_version(tool: str) -> str:
    """The first line of `<tool> --version`, or an empty string when the tool is missing."""
    path = shutil.which(tool)
    if not path:
        return ""
    done = subprocess.run(
        [path, "--version"], capture_output=True, text=True, encoding="utf-8", check=False
    )
    return done.stdout.strip().splitlines()[0] if done.returncode == 0 and done.stdout else ""


def run(cmd: list[str], cwd: Path) -> None:
    """Run a step with its output on stderr (stdout of a SessionStart hook goes to the agent)."""
    sys.stderr.write(f"session-start: {' '.join(cmd)}\n")
    subprocess.run(cmd, cwd=cwd, stdout=sys.stderr, stderr=sys.stderr, check=True)


def install_tools(root: Path) -> None:
    """The CLI tools at the pinned versions, installed only when missing or different."""
    if PNPM_VERSION not in tool_version("pnpm"):
        run(["npm", "install", "-g", f"pnpm@{PNPM_VERSION}"], root)
    if JUST_VERSION not in tool_version("just"):
        run(["uv", "tool", "install", "--force", f"rust-just=={JUST_VERSION}"], root)
    if "prek 0.5." not in tool_version("prek"):
        run(["uv", "tool", "install", "--force", PREK_SPEC], root)
    if OPENSPEC_VERSION not in tool_version("openspec"):
        run(["npm", "install", "-g", f"@fission-ai/openspec@{OPENSPEC_VERSION}"], root)


def install_dependencies(root: Path) -> None:
    """The steps of `just setup`: harness, backend and frontend packages, then the git hooks."""
    run(["uv", "sync"], root)
    run(["uv", "sync", "--directory", "backend"], root)
    run(["pnpm", "--dir", "frontend", "install"], root)
    run(["prek", "install"], root)


def main() -> int:
    """Install everything in a cloud session; skip elsewhere."""
    if os.environ.get("CLAUDE_CODE_REMOTE") != "true":
        return 0
    root = project_dir()
    # uv tool puts just and prek here; later steps of this hook and the session need them on PATH.
    tool_bin = Path.home() / ".local/bin"
    os.environ["PATH"] = f"{tool_bin}{os.pathsep}{os.environ.get('PATH', '')}"
    env_file = os.environ.get("CLAUDE_ENV_FILE")
    if env_file:
        with Path(env_file).open("a", encoding="utf-8") as fh:
            fh.write(f'export PATH="{tool_bin}:$PATH"\n')
    try:
        install_tools(root)
        install_dependencies(root)
    except (subprocess.CalledProcessError, OSError) as exc:
        sys.stderr.write(f"session-start: failed: {exc}\n")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
