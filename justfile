# Project commands. Conditional logic goes through Python so it works in PowerShell and sh.
# `dev`, `db` and `test-db` come with task 0.1.
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# List the recipes
default:
    @just --list

# Install dependencies and the git hooks (the frontend only when it exists)
setup:
    uv sync
    prek install
    uv run --no-project python -c "import pathlib, shutil, subprocess; f = pathlib.Path('frontend/package.json'); subprocess.run([shutil.which('pnpm') or 'pnpm', '--dir', 'frontend', 'install'], check=True) if f.is_file() else print('no frontend yet: skipped')"

# Run every static check (read-only): ruff, pyright, doc checkers, openspec, hygiene hooks
check:
    uv run --no-project python scripts/run_checks.py

# Format and auto-fix the code (backend and frontend when present)
format:
    uv run ruff format
    uv run ruff check --fix
    uv run --no-project python -c "import pathlib, shutil, subprocess; steps = [(pathlib.Path('backend/pyproject.toml'), ['uv', 'run', '--directory', 'backend', 'ruff', 'format', '.']), (pathlib.Path('backend/pyproject.toml'), ['uv', 'run', '--directory', 'backend', 'ruff', 'check', '--fix', '.']), (pathlib.Path('frontend/package.json'), [shutil.which('pnpm') or 'pnpm', '--dir', 'frontend', 'format'])]; [subprocess.run(c, check=True) for p, c in steps if p.is_file()]"

# Run the unit tests
test:
    uv run --no-project python .claude/skills/test/scripts/run_tests.py . unit

# Run all tests, including the database suite
test-all:
    uv run --no-project python .claude/skills/test/scripts/run_tests.py . all
