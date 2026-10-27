"""Create and tear down TDD sandboxes: worktree, snapshot copy, dependency links, test database.

Why it exists: `tdd_sandbox.py create` must give `test-writer` a copy of the repo with the change's
artifacts but none of the change's code, its own database, and no way to disturb the checkout.
"""

from __future__ import annotations

import re
import shutil
import subprocess
import sys
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlsplit

import sandbox_common as sc

NAME_RE = re.compile(r"[a-z0-9][a-z0-9-]*")


def read_env(path: Path) -> dict[str, str]:
    """KEY=VALUE lines of a .env file (quotes stripped)."""
    values: dict[str, str] = {}
    try:
        lines = path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return values
    for line in lines:
        match = re.match(r"\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$", line)
        if match and not line.lstrip().startswith("#"):
            values[match.group(1)] = match.group(2).strip("'\"")
    return values


def compose(root: Path, *args: str) -> tuple[int, str]:
    """Run `docker compose <args>` in the checkout; (exit code, combined output)."""
    docker = shutil.which("docker")
    if docker is None:
        return 127, "docker not found"
    try:
        proc = subprocess.run(
            [docker, "compose", *args],
            cwd=root,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=120,
            check=False,
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return 1, str(exc)
    return proc.returncode, (proc.stdout + proc.stderr).strip()


def setup_database(root: Path, sandbox: Path, name: str) -> dict[str, Any] | None:
    """Create `<db>_sbx_<name>` and write the sandbox .env; returns the db record or None."""
    env_file = root / ".env"
    url = read_env(env_file).get("TEST_DATABASE_URL")
    if not (root / "docker-compose.yml").is_file() or not url:
        sys.stdout.write("Database: not configured (no docker-compose.yml or TEST_DATABASE_URL)\n")
        return None
    parts = urlsplit(url)
    base_db = parts.path.lstrip("/")
    user = parts.username or "postgres"
    new_db = f"{base_db}_sbx_{name.replace('-', '_')}"
    code, out = compose(root, "exec", "-T", "db", "createdb", "-U", user, new_db)
    if code != 0 and "already exists" not in out:
        sys.stdout.write(
            f"Database: the db container is down or createdb failed ({out[:200]}).\n"
            "  The database tests will be SKIPPED in this sandbox. Start it with "
            "`docker compose up -d db`, then drop and create the sandbox again.\n"
        )
        return None
    new_url = parts._replace(path="/" + new_db).geturl()
    text = env_file.read_text(encoding="utf-8")
    text = re.sub(
        r"^(\s*TEST_DATABASE_URL\s*=).*$", lambda m: m.group(1) + new_url, text, flags=re.M
    )
    (sandbox / ".env").write_text(text, encoding="utf-8", newline="\n")
    sys.stdout.write(
        f"Database: created {new_db}; the sandbox .env points TEST_DATABASE_URL at it\n"
    )
    return {"user": user, "name": new_db}


def drop_database(root: Path, db: dict[str, Any] | None) -> None:
    """Best-effort `dropdb` of a sandbox database."""
    if not db:
        return
    code, out = compose(
        root, "exec", "-T", "db", "dropdb", "--if-exists", "-U", str(db["user"]), str(db["name"])
    )
    if code != 0:
        sys.stderr.write(f"Could not drop database {db['name']}: {out[:200]}\n")


def sandbox_block(name: str, path: Path, has_db: bool) -> str:
    """The «Sandbox» block for test-writer's brief (no path into the main checkout)."""
    db_line = (
        "- Database tests run against this sandbox's own database."
        if has_db
        else "- Database tests will be SKIPPED here (no sandbox database); write them anyway."
    )
    return "\n".join(
        [
            "## Sandbox",
            f"Name: {name}",
            f"Path: {path}",
            "Rules:",
            "- Work only inside this directory: read, search, edit and run everything here.",
            "- Never read, search or edit anything outside it; never touch the main checkout.",
            "- The code of the change does not exist here: tests describe the spec and fail.",
            "- Test files go to: backend/app/**/test_*.py, backend/tests/**, "
            "frontend/src/**/*.test.ts(x).",
            "- Backend tests: uv run --directory backend pytest <files> -q -rA",
            "- Frontend tests: pnpm --dir frontend exec vitest run <files> --reporter=verbose",
            db_line,
            "- Do not use just, make, docker, alembic or git commit/push/checkout/reset/stash.",
        ]
    )


def create(root: Path, name: str, base: Path | None) -> int:
    """`create`: worktree at HEAD, snapshot of uncommitted files, links, database, registry."""
    if not NAME_RE.fullmatch(name):
        sys.stderr.write("Sandbox name: lowercase letters, digits and dashes only\n")
        return 2
    if not sc.has_head(root):
        sys.stderr.write("The repository has no commits yet: a sandbox needs HEAD. Commit first.\n")
        return 2
    boxes = sc.load_registry(root)
    if name in boxes:
        sys.stderr.write(f"Sandbox {name!r} already exists (see `list`); drop it first.\n")
        return 1
    parent = (base or root.parent / f"{root.name}-sandboxes").resolve()
    path = parent / name
    if path.exists():
        sys.stderr.write(f"{path} already exists\n")
        return 1
    parent.mkdir(parents=True, exist_ok=True)
    code, out = sc.git(root, "worktree", "add", "--detach", str(path), "HEAD")
    if code != 0:
        sys.stderr.write(f"git worktree add failed: {out}\n")
        return 2
    present, deleted = sc.changed_files(root)
    snapshot: dict[str, str | None] = {}
    for rel in present:
        target = path / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(root / rel, target)
        snapshot[rel] = sc.file_hash(root / rel)
    for rel in deleted:
        (path / rel).unlink(missing_ok=True)
        snapshot[rel] = None
    for rel in sc.all_files(root):
        if sc.is_test_file(rel) and rel not in snapshot:
            snapshot[rel] = sc.file_hash(root / rel)
    link_notes = link_dependencies(root, path)
    db = setup_database(root, path, name)
    for note in link_notes:
        sys.stdout.write(note + "\n")
    boxes[name] = {
        "name": name,
        "path": str(path),
        "base": sc.head_sha(root),
        "created": date.today().isoformat(),
        "snapshot": snapshot,
        "db": db,
    }
    sc.save_registry(root, boxes)
    sys.stdout.write("\n" + sandbox_block(name, path, db is not None) + "\n")
    return 0


def link_dependencies(root: Path, sandbox: Path) -> list[str]:
    """Link dependency folders from the checkout; returns notes about the result."""
    notes: list[str] = []
    for rel in sc.DEP_FOLDERS:
        source = root / rel
        if not source.is_dir():
            continue
        err = sc.make_link(sandbox / rel, source)
        notes.append(f"Linked {rel}" if err is None else f"Could not link {rel}: {err}")
    return notes


def remove_sandbox(root: Path, box: dict[str, Any]) -> None:
    """Remove worktree, links, database and the registry entry of a sandbox."""
    path = Path(str(box["path"]))
    sc.remove_links(path)
    code, out = sc.git(root, "worktree", "remove", "--force", str(path))
    if code != 0:
        sys.stderr.write(f"git worktree remove: {out.strip()}\n")
    if path.exists():
        shutil.rmtree(path, ignore_errors=True)
    sc.git(root, "worktree", "prune")
    drop_database(root, box.get("db"))
    boxes = sc.load_registry(root)
    boxes.pop(str(box["name"]), None)
    sc.save_registry(root, boxes)
