"""Doc plan: which docs a change should touch, split into small portions.

A cheap model writes docs well only with a small scope and a list of what to touch. `plan`
splits the changed files into portions of at most 15 files by area and lists, per portion,
the docs it should touch, from the path-pattern table EXPECTED_DOCS (the same mapping as the
`docs-sync` rule). The commit preflight imports the same table.

Usage: uv run --no-project python doc_plan.py <project-dir> plan
"""

from __future__ import annotations

import argparse
import io
import logging
import re
import subprocess
import sys
from pathlib import Path

LOG = logging.getLogger("doc_plan")
PORTION_SIZE = 15

ARCH = "docs/architecture.md"
TECH = "docs/tech.md"
GUIDE = "docs/guide/<area>.md"
TOOLING_DOCS = [f"{TECH} «Dev environment and checks»", "CLAUDE.md «Commands»"]

# (glob, docs targets). A target is "<file> «Heading»", "<file>" or "docstrings". The glob
# dialect: `**/` = any directories (or none), `**` = anything, `*` = anything inside one name.
# GUIDE is resolved to the guide article of the file's area.
EXPECTED_DOCS: list[tuple[str, list[str]]] = [
    ("backend/migrations/**", [f"{ARCH} «Data model»"]),
    ("backend/app/**/models.py", [f"{ARCH} «Data model»"]),
    ("backend/app/**/router.py", [f"{ARCH} «Routes and API»"]),
    ("backend/app/**", [GUIDE, "docstrings"]),
    ("frontend/src/**", [GUIDE, "docstrings"]),
    ("backend/app/platform/settings.py", [f"{TECH} «Environment variables»"]),
    (".env.example", [f"{TECH} «Environment variables»"]),
    ("backend/pyproject.toml", [f"{TECH} «Stack»"]),
    ("frontend/package.json", [f"{TECH} «Stack»"]),
    ("pyproject.toml", [f"{TECH} «Stack»"]),
    ("justfile", TOOLING_DOCS),
    ("scripts/**", TOOLING_DOCS),
    (".pre-commit-config.yaml", TOOLING_DOCS),
    ("docker-compose.yml", [f"{ARCH} «Deploy»"]),
    ("**/Dockerfile*", [f"{ARCH} «Deploy»"]),
]

# Paths that never expect docs of their own (generated code, tests).
EXCLUDED = [
    "frontend/src/api/generated/**",
    "**/test_*.py",
    "**/*_test.py",
    "**/conftest.py",
    "backend/tests/**",
    "**/*.test.ts",
    "**/*.test.tsx",
    "**/__tests__/**",
    "**/__pycache__/**",
]
STRUCTURE_TARGET = f"{ARCH} «Repository structure»"
STRUCTURE_SKIP = [
    "docs/**",
    "openspec/**",
    ".claude/**",
    "**/*.lock",
    ".gitignore",
    "CHANGELOG.md",
    "README.md",
    "CLAUDE.md",
]


def glob_to_regex(glob: str) -> re.Pattern[str]:
    """Translate the small glob dialect above to a compiled regex."""
    out: list[str] = []
    i = 0
    while i < len(glob):
        if glob.startswith("**/", i):
            out.append("(?:.*/)?")
            i += 3
        elif glob.startswith("**", i):
            out.append(".*")
            i += 2
        elif glob[i] == "*":
            out.append("[^/]*")
            i += 1
        elif glob[i] == "?":
            out.append("[^/]")
            i += 1
        else:
            out.append(re.escape(glob[i]))
            i += 1
    return re.compile("".join(out) + r"\Z")


def matches(path: str, glob: str) -> bool:
    """Return True when a posix relative path matches the glob."""
    return glob_to_regex(glob).match(path) is not None


def _backend_area(parts: list[str]) -> str:
    if len(parts) > 4 and parts[1:3] == ["app", "modules"]:
        return f"backend/{parts[3]}"
    if len(parts) > 3 and parts[1] == "app":
        return f"backend/{parts[2]}"
    return "backend/migrations" if parts[1:2] == ["migrations"] else "backend"


def area_of(path: str) -> str:
    """Name the area (backend module, frontend area, infra, tooling...) of a path."""
    parts = path.split("/")
    name = parts[-1]
    if parts[0] == "backend":
        return _backend_area(parts)
    if parts[0] == "frontend":
        return f"frontend/{parts[2]}" if len(parts) > 3 and parts[1] == "src" else "frontend"
    if name == "docker-compose.yml" or name.startswith("Dockerfile") or name == ".env.example":
        return "infra"
    tooling_names = {"justfile", ".pre-commit-config.yaml", "pyproject.toml", "package.json"}
    if parts[0] in {"scripts", ".claude"} or name in tooling_names:
        return "tooling"
    return parts[0] if len(parts) > 1 else "root"


def guide_target(path: str) -> str:
    """Return the guide article of the area a path belongs to."""
    area = area_of(path)
    slug = area.removeprefix("backend/") if area.startswith("backend/") else area
    return f"docs/guide/{slug.replace('/', '-')}.md"


def expected_docs_for(paths: list[str], new_paths: list[str] | None = None) -> dict[str, list[str]]:
    """Map each docs target to the changed paths that make it expected.

    `new_paths` are the added or renamed files; they also expect the repository structure.
    """
    result: dict[str, list[str]] = {}
    for path in paths:
        if any(matches(path, g) for g in EXCLUDED):
            continue
        for glob, targets in EXPECTED_DOCS:
            if not matches(path, glob):
                continue
            for target in targets:
                key = guide_target(path) if target == GUIDE else target
                if path not in result.setdefault(key, []):
                    result[key].append(path)
    for path in new_paths or []:
        skip = EXCLUDED + STRUCTURE_SKIP
        if not any(matches(path, g) for g in skip):
            found = result.setdefault(STRUCTURE_TARGET, [])
            if path not in found:
                found.append(path)
    return {k: v for k, v in result.items() if v}


def git(root: Path, *args: str) -> tuple[int, str]:
    """Run git in root; return (exit code, stdout). Never raises."""
    try:
        done = subprocess.run(
            ["git", "-C", str(root), *args],
            capture_output=True,
            text=True,
            encoding="utf-8",
            check=False,
        )
    except OSError as err:
        LOG.warning("git is not available: %s", err)
        return 127, ""
    return done.returncode, done.stdout


def _parse_name_status(text: str, into: dict[str, str]) -> None:
    for line in text.splitlines():
        cols = line.split("\t")
        if len(cols) < 2:
            continue
        code = cols[0][0]
        if code in "RC" and len(cols) >= 3:
            if code == "R":
                into[cols[1]] = "D"
            into[cols[2]] = "R" if code == "R" else "A"
        else:
            into[cols[1]] = code


def changed_files(root: Path) -> dict[str, str]:
    """Return {posix path: status} of the change: branch vs main, staged, unstaged, untracked.

    Status is A, M, D, R (renamed target), T, or `?` for untracked. Works with no commits and
    with no `main` branch.
    """
    result: dict[str, str] = {}
    code, text = git(root, "diff", "--name-status", "main...HEAD")
    if code == 0:
        _parse_name_status(text, result)
    for extra in (["--cached"], []):
        code, text = git(root, "diff", "--name-status", *extra)
        if code == 0:
            _parse_name_status(text, result)
    code, text = git(root, "ls-files", "--others", "--exclude-standard")
    if code == 0:
        for line in text.splitlines():
            if line.strip():
                result[line.strip()] = "?"
    return result


def make_portions(paths: list[str]) -> list[tuple[str, list[str]]]:
    """Group paths by area, then cut every group into portions of at most PORTION_SIZE."""
    groups: dict[str, list[str]] = {}
    for path in sorted(paths):
        groups.setdefault(area_of(path), []).append(path)
    portions: list[tuple[str, list[str]]] = []
    for area, files in sorted(groups.items()):
        for i in range(0, len(files), PORTION_SIZE):
            portions.append((area, files[i : i + PORTION_SIZE]))
    return portions


def render_plan(changes: dict[str, str]) -> str:
    """Render the plan text for the changed files."""
    new = {p for p, s in changes.items() if s in {"A", "R", "?"}}
    lines: list[str] = []
    count = 0
    for area, files in make_portions(list(changes)):
        expected = expected_docs_for(files, [f for f in files if f in new])
        if not expected:
            continue
        count += 1
        lines.append(f"Portion {count}: {area} [{len(files)}]")
        lines.append("  Files: " + ", ".join(files))
        lines.append("  Docs to touch:")
        lines.extend(f"  - {target}  <- {', '.join(src[:3])}" for target, src in expected.items())
    return "\n".join(lines) if lines else "Nothing to document"


def main(argv: list[str] | None = None) -> int:
    """Entry point."""
    if isinstance(sys.stdout, io.TextIOWrapper):
        sys.stdout.reconfigure(encoding="utf-8")
    parser = argparse.ArgumentParser(description="Plan the docs a change should touch.")
    parser.add_argument("project_dir")
    parser.add_argument("command", choices=["plan"])
    args = parser.parse_args(argv)
    root = Path(args.project_dir).resolve()
    sys.stdout.write(render_plan(changed_files(root)) + "\n")
    return 0


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, stream=sys.stderr)
    sys.exit(main())
