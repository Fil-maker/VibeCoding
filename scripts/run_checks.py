"""The body of ``just check``: every static check, read-only, run to the end.

Why: one command that reports each check as ``PASS``/``FAIL <name>`` with the failing output
trimmed, so an agent sees everything that is broken at once. Warnings fail. Backend and
frontend checks (including that the generated API client is fresh) run only when those parts
exist. The in-place fixers (end-of-file, trailing whitespace) are not run here because they
would modify files; the commit hook runs them. Exit 1 if any check failed.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

LOG = logging.getLogger("run_checks")
ROOT = Path(__file__).resolve().parent.parent
MAX_OUTPUT_LINES = 25
MAX_OUTPUT_CHARS = 2500
HYGIENE_HOOKS = ["check-added-large-files", "check-yaml", "check-toml", "check-merge-conflict"]
DOC_SCRIPTS = {
    "doc-links": "scripts/check_doc_links.py",
    "doc-facts": "scripts/check_doc_facts.py",
}


@dataclass
class Check:
    """One check: a name, a command, and optional pass/fail overrides."""

    name: str
    cmd: list[str]
    required_file: str | None = None
    ok_if_output_has: str | None = None


def uv(*args: str) -> list[str]:
    """A uv command line."""
    return [shutil.which("uv") or "uv", *args]


def harness_checks() -> list[Check]:
    """Checks of the harness Python, docs, specs and hygiene."""
    checks = [
        Check("ruff-check", uv("run", "ruff", "check")),
        Check("ruff-format", uv("run", "ruff", "format", "--check")),
        Check("pyright", uv("run", "pyright", "--warnings")),
    ]
    for name, script in DOC_SCRIPTS.items():
        checks.append(
            Check(name, uv("run", "--no-project", "python", script, "."), required_file=script)
        )
    openspec = shutil.which("openspec")
    checks.append(
        Check(
            "openspec-validate",
            [openspec or "openspec", "validate", "--specs", "--strict"],
            ok_if_output_has="no specs",
        )
    )
    prek = shutil.which("prek") or "prek"
    checks.extend(Check(f"hook-{h}", [prek, "run", h, "--all-files"]) for h in HYGIENE_HOOKS)
    return checks


def product_checks() -> list[Check]:
    """Backend and frontend checks, when those parts exist."""
    checks: list[Check] = []
    if (ROOT / "backend/pyproject.toml").is_file():
        base = ["run", "--directory", "backend"]
        checks += [
            Check("backend-ruff-check", uv(*base, "ruff", "check", ".")),
            Check("backend-ruff-format", uv(*base, "ruff", "format", "--check", ".")),
            Check("backend-pyright", uv(*base, "pyright", "--warnings")),
        ]
    if (ROOT / "frontend/package.json").is_file():
        pnpm = shutil.which("pnpm") or "pnpm"
        checks += [
            Check("frontend-lint", [pnpm, "--dir", "frontend", "lint", "--max-warnings", "0"]),
            Check("frontend-typecheck", [pnpm, "--dir", "frontend", "typecheck"]),
            Check("frontend-format", [pnpm, "--dir", "frontend", "format:check"]),
            Check(
                "frontend-api-client",
                uv("run", "--no-project", "python", "scripts/api_client.py", ".", "check"),
                required_file="scripts/api_client.py",
            ),
        ]
    return checks


def trim(text: str) -> str:
    """The tail of the output, bounded in lines and characters."""
    lines = text.strip().splitlines()[-MAX_OUTPUT_LINES:]
    out = "\n".join(lines)
    return out[-MAX_OUTPUT_CHARS:]


def run_check(check: Check) -> tuple[bool, str]:
    """Run one check; returns (passed, output)."""
    if check.required_file and not (ROOT / check.required_file).is_file():
        return False, f"missing: {check.required_file}"
    if shutil.which(check.cmd[0]) is None and not Path(check.cmd[0]).is_file():
        return False, f"missing tool: {check.cmd[0]}"
    try:
        res = subprocess.run(
            check.cmd,
            cwd=ROOT,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        return False, f"cannot start: {exc}"
    out = res.stdout + res.stderr
    if res.returncode == 0:
        return True, out
    if check.ok_if_output_has and check.ok_if_output_has in out.lower():
        return True, out
    return False, trim(out)


def main() -> int:
    """Entry point."""
    cast("Any", sys.stdout).reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    argparse.ArgumentParser(description="Run every static check; exit 1 if any fails.").parse_args()
    failed = 0
    for check in [*harness_checks(), *product_checks()]:
        passed, out = run_check(check)
        sys.stdout.write(f"{'PASS' if passed else 'FAIL'} {check.name}\n")
        if not passed:
            failed += 1
            sys.stdout.write("".join(f"    {ln}\n" for ln in out.splitlines()))
    sys.stdout.write(f"{failed} check(s) failed\n" if failed else "all checks passed\n")
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
