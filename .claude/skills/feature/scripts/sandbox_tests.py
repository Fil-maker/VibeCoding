"""Run backend and frontend tests for the TDD sandbox and classify what they report.

Why it exists: the red check must read pytest and vitest output the same way every time:
RED needs a reason (missing interface name or a THEN value), GREEN and PARTIAL are told apart,
and tests skipped because the database is down must not look like passes.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

TIMEOUT_SECONDS = 900
MARKS = "✓✔√↓✗xX" + chr(0xD7)  # vitest verbose result marks
MISSING_NAME = re.compile(
    r"ImportError|ModuleNotFoundError|AttributeError|NameError|ReferenceError|is not exported"
    r"|Cannot find module|Failed to resolve import|does not provide an export|is not defined"
    r"|is not a function|is not a constructor|No module named"
)
THEN_VALUE = re.compile(r"AssertionError|^assert\b|expected .* to |toEqual|toBe\b|toHaveBeen", re.I)


@dataclass
class TestResult:
    """One test (or one skipped group) from a run."""

    __test__ = False  # not a pytest class

    file: str
    name: str
    outcome: str  # passed | failed | skipped
    reason: str = ""


@dataclass
class RunReport:
    """Results of one run plus problems that stopped part of it."""

    results: list[TestResult] = field(default_factory=lambda: [])
    notes: list[str] = field(default_factory=lambda: [])


def classify(reason: str) -> str:
    """Reason class of a failure: missing interface name, THEN value, or other."""
    if MISSING_NAME.search(reason):
        return "missing interface name"
    if THEN_VALUE.search(reason):
        return "THEN value"
    short = reason.strip().splitlines()[0][:100] if reason.strip() else "no message"
    return f"other: {short}"


def map_file(name: str, requested: list[str]) -> str:
    """Map a path printed by a runner to the requested repo-relative path."""
    clean = name.replace("\\", "/").lstrip("./")
    for rel in requested:
        if rel == clean or rel.endswith("/" + clean):
            return rel
    return clean


def pytest_errors(output: str) -> dict[str, str]:
    """First `E   ` line of each failure or collection-error section, keyed by section title."""
    found: dict[str, str] = {}
    title = ""
    for line in output.splitlines():
        head = re.match(r"_{3,} (?:ERROR collecting )?(.+?) _{3,}\s*$", line)
        if head:
            title = head.group(1)
        elif title and title not in found and line.startswith("E   "):
            found[title] = line[4:].strip()
    return found


def parse_pytest(output: str, requested: list[str]) -> list[TestResult]:
    """Results from `pytest -q -rA` short summary lines."""
    results: list[TestResult] = []
    errors = pytest_errors(output)
    in_summary = False
    for line in output.splitlines():
        if re.match(r"=+ short test summary info =+$", line.strip()):
            in_summary = True
            continue
        if not in_summary:
            continue  # captured log lines above the summary also start with ERROR
        match = re.match(r"(PASSED|FAILED|ERROR|SKIPPED)\s+(.*)$", line)
        if not match:
            continue
        kind, rest = match.groups()
        if kind == "SKIPPED":
            skip = re.match(r"\[(\d+)\]\s+(.+?):\d+:\s*(.*)", rest)
            if skip:
                for _ in range(int(skip.group(1))):
                    results.append(
                        TestResult(map_file(skip.group(2), requested), "", "skipped", skip.group(3))
                    )
            continue
        node, _, reason = rest.partition(" - ")
        path, _, test = node.partition("::")
        outcome = "passed" if kind == "PASSED" else "failed"
        reason = reason.strip() or errors.get(test.split("::")[-1] or path, "")
        results.append(TestResult(map_file(path, requested), test, outcome, reason))
    return results


def parse_vitest(output: str, requested: list[str]) -> list[TestResult]:
    """Results from `vitest run --reporter=verbose`."""
    reasons: dict[tuple[str, str], str] = {}
    current: tuple[str, str] | None = None
    for line in output.splitlines():
        head = re.match(r"\s*FAIL\s+(\S+)(?:\s+>\s+(.+?)|\s+\[.*\])?\s*$", line)
        if head:
            current = (map_file(head.group(1), requested), (head.group(2) or "").strip())
            reasons[current] = ""
        elif current and not line.strip().startswith("⎯"):
            reasons[current] += line.strip() + "\n"
        elif current:
            current = None
    results: list[TestResult] = []
    for line in output.splitlines():
        row = re.match(r"\s*(\S)\s+(\S+\.test\.tsx?)(?:\s+>\s+(.*?))?(?:\s+\d+ms)?\s*$", line)
        if not row or row.group(1) not in MARKS:
            continue
        symbol, file, name = row.groups()
        path = map_file(file, requested)
        name = (name or "").strip()
        if symbol == "↓":
            results.append(TestResult(path, name, "skipped"))
        elif symbol in "✓✔√":
            results.append(TestResult(path, name, "passed"))
        else:
            results.append(TestResult(path, name, "failed", reasons.get((path, name), "")))
    seen = {r.file for r in results}
    for (path, name), reason in reasons.items():
        if not name and path not in seen:  # the whole file failed before any test ran
            results.append(TestResult(path, "(file)", "failed", reason))
    return results


def _run(cmd: list[str], cwd: Path, env: dict[str, str]) -> str:
    try:
        proc = subprocess.run(
            cmd,
            cwd=cwd,
            env=env,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=TIMEOUT_SECONDS,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return f"RUNNER-ERROR {exc}"
    return proc.stdout + "\n" + proc.stderr


def run_tests(root: Path, files: list[str], pythonpath_backend: bool = True) -> RunReport:
    """Run the given repo-relative test files inside `root` (a sandbox or the checkout)."""
    report = RunReport()
    env = {**os.environ, "COLUMNS": "300", "NO_COLOR": "1", "CI": "1", "PYTHONIOENCODING": "utf-8"}
    backend = [f for f in files if f.startswith("backend/")]
    frontend = [f for f in files if f.startswith("frontend/")]
    for rel in files:
        if rel not in backend and rel not in frontend:
            report.notes.append(f"no runner for {rel}")
    if backend:
        uv = shutil.which("uv")
        if uv is None:
            report.notes.append("uv not found: backend tests not run")
        else:
            if pythonpath_backend:
                env["PYTHONPATH"] = str(root / "backend")
            rels = [f.removeprefix("backend/") for f in backend]
            cmd = [
                uv,
                "run",
                "--directory",
                "backend",
                "pytest",
                *rels,
                "-q",
                "-rA",
                "--continue-on-collection-errors",
            ]
            out = _run(cmd, root, env)
            _collect(report, out, parse_pytest(out, backend), "pytest")
    if frontend:
        pnpm = shutil.which("pnpm")
        if pnpm is None:
            report.notes.append("pnpm not found: frontend tests not run")
        else:
            rels = [f.removeprefix("frontend/") for f in frontend]
            cmd = [pnpm, "--dir", "frontend", "exec", "vitest", "run", *rels, "--reporter=verbose"]
            out = _run(cmd, root, env)
            _collect(report, out, parse_vitest(out, frontend), "vitest")
    return report


def _collect(report: RunReport, out: str, results: list[TestResult], tool: str) -> None:
    report.results += results
    if "RUNNER-ERROR" in out or not results:
        tail = "\n".join(out.strip().splitlines()[-6:])
        report.notes.append(f"{tool} gave no parsable results:\n{tail}")


def verdict(file: str, results: list[TestResult]) -> tuple[str, str]:
    """(label, detail) for one test file: RED, GREEN, PARTIAL, SKIPPED or NOT FOUND."""
    mine = [r for r in results if r.file == file]
    if not mine:
        return "NOT FOUND", "no result in the run output"
    passed = [r for r in mine if r.outcome == "passed"]
    failed = [r for r in mine if r.outcome == "failed"]
    skipped = [r for r in mine if r.outcome == "skipped"]
    counts = f"{len(passed)} passed, {len(failed)} failed, {len(skipped)} skipped"
    if skipped and not passed and not failed:
        return "SKIPPED", f"{counts} (database down?): {skipped[0].reason}"
    if passed and (failed or skipped):
        names = ", ".join(r.name for r in passed[:5])
        return "PARTIAL", f"{counts}; passing without the code: {names}"
    if passed:
        return "GREEN", counts
    reasons = sorted({classify(r.reason) for r in failed})
    return "RED", f"{counts}; reason: {'; '.join(reasons)}"
