"""Generate the SPA's API client from the backend's OpenAPI schema, or check it is fresh.

Why: the schema FastAPI builds is the contract; ``frontend/src/api/openapi.json`` and
``frontend/src/api/generated/schema.ts`` are generated from it and committed. ``generate``
rewrites them (``just api-client``); ``check`` regenerates into a temporary directory and
fails when a committed file differs or is missing, leaving the repository untouched. ``just check``
runs it as ``frontend-api-client``. Exit 0 ok, 1 stale or a step failed.
"""

from __future__ import annotations

import argparse
import logging
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LOG = logging.getLogger("api_client")
SCHEMA_JSON = Path("frontend/src/api/openapi.json")
SCHEMA_TS = Path("frontend/src/api/generated/schema.ts")


def export_schema(project: Path, target: Path) -> None:
    """Write the OpenAPI schema printed by the backend to ``target``."""
    uv = shutil.which("uv") or "uv"
    res = subprocess.run(
        [uv, "run", "--directory", "backend", "python", "-m", "app.openapi"],
        cwd=project,
        capture_output=True,
        text=True,
        encoding="utf-8",
        check=True,
    )
    target.parent.mkdir(parents=True, exist_ok=True)
    # Bytes, so that Windows does not turn the line feeds into CRLF.
    target.write_bytes(res.stdout.encode("utf-8"))


def generate_types(project: Path, schema_json: Path, target: Path) -> None:
    """Generate the TypeScript types of ``schema_json`` into ``target``."""
    pnpm = shutil.which("pnpm") or "pnpm"
    target.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        [
            pnpm,
            "--dir",
            "frontend",
            "exec",
            "openapi-typescript",
            str(schema_json),
            "-o",
            str(target),
        ],
        cwd=project,
        check=True,
        capture_output=True,
        text=True,
        encoding="utf-8",
    )


def build(project: Path, out_json: Path, out_ts: Path) -> None:
    """Export the schema to ``out_json`` and generate the types from it into ``out_ts``."""
    export_schema(project, out_json)
    generate_types(project, out_json, out_ts)


def stale_files(project: Path) -> list[Path]:
    """Committed generated files that differ from a fresh generation."""
    with tempfile.TemporaryDirectory() as tmp:
        fresh_json = Path(tmp) / "openapi.json"
        fresh_ts = Path(tmp) / "schema.ts"
        build(project, fresh_json, fresh_ts)
        pairs = [(SCHEMA_JSON, fresh_json), (SCHEMA_TS, fresh_ts)]
        return [
            committed
            for committed, fresh in pairs
            if not (project / committed).is_file()
            or (project / committed).read_bytes() != fresh.read_bytes()
        ]


def main() -> int:
    """Entry point."""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stderr)
    ap = argparse.ArgumentParser(description="Generate or check the SPA API client.")
    ap.add_argument("project_dir", type=Path)
    ap.add_argument("command", choices=["generate", "check"])
    args = ap.parse_args()
    project: Path = args.project_dir.resolve()
    try:
        if args.command == "generate":
            build(project, project / SCHEMA_JSON, project / SCHEMA_TS)
            sys.stdout.write(f"generated {SCHEMA_JSON} and {SCHEMA_TS}\n")
            return 0
        stale = stale_files(project)
    except subprocess.CalledProcessError as exc:
        sys.stdout.write(f"step failed: {exc.cmd}\n{(exc.stderr or '')[-1500:]}\n")
        return 1
    if stale:
        names = ", ".join(p.as_posix() for p in stale)
        sys.stdout.write(f"stale: {names}; run `just api-client` and commit the result\n")
        return 1
    sys.stdout.write("the API client is up to date\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
