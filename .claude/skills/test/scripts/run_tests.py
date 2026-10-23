"""Run the project's test suites and print a short, pasteable result.

Why: one command that knows which suites exist, when the database suite is needed, and what
the database suite requires (``.env``, Docker, the ``db`` container), so an agent gets counts
and failing tests instead of raw logs. Full logs go to ``.cache/tests/<suite>.log``.
Exit 0 all passed, 1 a suite failed, 2 the environment is not ready.
"""

from __future__ import annotations

import argparse
import logging
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, cast

LOG = logging.getLogger("run_tests")
DB_TRIGGERS = [
    re.compile(r"^backend/app/.+/(service|repository|models)\.py$"),
    re.compile(r"^backend/migrations/"),
    re.compile(r"^backend/tests/integration/"),
]
MAX_FAIL_LINES = 40
PG_WAIT_SECONDS = 60


@dataclass
class Suite:
    """A test suite: its name, command, and working directory."""

    name: str
    cmd: list[str]
    present: bool


class EnvNotReadyError(Exception):
    """The database suite cannot run: the message says what is missing."""


def build_suites(project: Path, flt: str | None) -> dict[str, Suite]:
    """All known suites, with the filter applied to their commands."""
    uv = shutil.which("uv") or "uv"
    pnpm = shutil.which("pnpm") or "pnpm"
    backend = (project / "backend/pyproject.toml").is_file()
    frontend = (project / "frontend/package.json").is_file()
    integ = (project / "backend/tests/integration").is_dir()
    k = ["-k", flt] if flt else []
    t = ["-t", flt] if flt else []
    return {
        "backend-unit": Suite(
            "backend-unit",
            [uv, "run", "--directory", "backend", "pytest", "app", "-q", *k],
            backend,
        ),
        "frontend-unit": Suite(
            "frontend-unit", [pnpm, "--dir", "frontend", "exec", "vitest", "run", *t], frontend
        ),
        "db": Suite(
            "db",
            [uv, "run", "--directory", "backend", "pytest", "tests/integration", "-q", *k],
            backend and integ,
        ),
    }


def changed_files(project: Path) -> list[str] | None:
    """Files changed versus main plus uncommitted ones; None when git cannot tell."""
    names: set[str] = set()
    ok = False
    for args in (["diff", "--name-only", "main"], ["diff", "--name-only", "HEAD"]):
        res = subprocess.run(
            ["git", "-C", str(project), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
        if res.returncode == 0:
            ok = True
            names.update(res.stdout.split())
    res = subprocess.run(
        ["git", "-C", str(project), "status", "--porcelain"],
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=False,
    )
    if res.returncode == 0:
        ok = True
        names.update(ln[3:].strip().strip('"') for ln in res.stdout.splitlines() if ln[3:])
    return sorted(names) if ok else None


def wants_db(project: Path) -> bool:
    """Whether auto mode should include the database suite."""
    files = changed_files(project)
    if not files:
        return True
    return any(p.match(f.replace("\\", "/")) for f in files for p in DB_TRIGGERS)


def run(
    cmd: list[str], cwd: Path, timeout: float | None = None
) -> subprocess.CompletedProcess[str]:
    """Run a command capturing text output."""
    return subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, encoding="utf-8", errors="replace",
        check=False, timeout=timeout,
    )  # fmt: skip


def prepare_db(project: Path) -> None:
    """Check .env and Docker, start the db container, wait for Postgres."""
    env = project / ".env"
    if not env.is_file() or not re.search(
        r"^\s*TEST_DATABASE_URL\s*=\s*\S", env.read_text("utf-8"), re.M
    ):
        raise EnvNotReadyError("TEST_DATABASE_URL is missing in .env (copy it from .env.example)")
    docker = shutil.which("docker")
    if docker is None:
        raise EnvNotReadyError("docker is not installed or not on PATH")
    if run([docker, "info"], project, 60).returncode != 0:
        raise EnvNotReadyError("docker is not running: start Docker Desktop and retry")
    up = run([docker, "compose", "up", "-d", "db"], project, 300)
    if up.returncode != 0:
        raise EnvNotReadyError(f"'docker compose up -d db' failed: {up.stderr.strip()[-300:]}")
    deadline = time.monotonic() + PG_WAIT_SECONDS
    while time.monotonic() < deadline:
        ready = run([docker, "compose", "exec", "-T", "db", "pg_isready"], project, 30)
        if ready.returncode == 0:
            return
        time.sleep(2)
    raise EnvNotReadyError(f"the db container was not ready after {PG_WAIT_SECONDS} s")


def summarise(log: str) -> tuple[str, list[str]]:
    """A summary line and the failing-test lines out of a pytest or vitest log."""
    lines = log.splitlines()
    summary = ""
    for ln in reversed(lines):
        if re.search(r"\d+ (passed|failed|error)|Tests\s+\d+|no tests ran|No test files", ln):
            summary = ln.strip(" =")
            break
    fails = [
        ln.rstrip()
        for ln in lines
        if ln.startswith(("FAILED ", "ERROR ", "E  ", " FAIL ", "FAIL ", "AssertionError"))
    ]
    return summary or "(no summary line found)", fails[:MAX_FAIL_LINES]


def run_suite(project: Path, suite: Suite) -> bool:
    """Run one suite, write its log, print its result; True when it passed."""
    try:
        res = run(suite.cmd, project)
    except OSError as exc:
        sys.stdout.write(f"{suite.name}: FAILED TO START ({exc})\n")
        return False
    log = res.stdout + ("\n" + res.stderr if res.stderr else "")
    logdir = project / ".cache/tests"
    logdir.mkdir(parents=True, exist_ok=True)
    (logdir / f"{suite.name}.log").write_text(log, encoding="utf-8")
    summary, fails = summarise(log)
    status = "PASSED" if res.returncode == 0 else "FAILED"
    sys.stdout.write(f"{suite.name}: {status} - {summary} (log: .cache/tests/{suite.name}.log)\n")
    for ln in fails if res.returncode != 0 else []:
        sys.stdout.write(f"    {ln}\n")
    return res.returncode == 0


def main() -> int:
    """Entry point."""
    cast("Any", sys.stdout).reconfigure(encoding="utf-8")
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    ap = argparse.ArgumentParser(description="Run the test suites.")
    ap.add_argument("project_dir", type=Path)
    ap.add_argument("mode", nargs="?", default="auto", choices=["auto", "unit", "db", "all"])
    ap.add_argument("filter", nargs="?", help="test name filter (-k for pytest, -t for vitest)")
    args = ap.parse_args()
    project: Path = args.project_dir.resolve()
    suites = build_suites(project, args.filter)
    mode: str = args.mode
    names: list[str] = []
    if mode in ("auto", "unit", "all"):
        names += ["backend-unit", "frontend-unit"]
    if mode in ("db", "all") or (mode == "auto" and wants_db(project)):
        names.append("db")
    present = [suites[n] for n in names if suites[n].present]
    for n in names:
        if not suites[n].present:
            sys.stdout.write(f"{n}: NOT PRESENT (created by task 0.1)\n")
    if not present:
        sys.stdout.write("no test suites exist yet\n")
        return 0
    failed = False
    not_ready = False
    for suite in present:
        if suite.name == "db":
            try:
                prepare_db(project)
            except EnvNotReadyError as exc:
                sys.stdout.write(f"db: ENVIRONMENT NOT READY - {exc}\n")
                not_ready = True
                continue
        failed = not run_suite(project, suite) or failed
    if not_ready:
        return 2
    return 1 if failed else 0


if __name__ == "__main__":
    raise SystemExit(main())
