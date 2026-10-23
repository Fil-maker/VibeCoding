# Project commands. Conditional logic goes through Python so it works in PowerShell and sh.
set windows-shell := ["powershell.exe", "-NoLogo", "-NoProfile", "-Command"]

# List the recipes
default:
    @just --list

# Install the dependencies (harness, backend, frontend) and the git hooks
setup:
    uv sync
    uv sync --directory backend
    pnpm --dir frontend install
    prek install

# Start the whole dev stack (database, backend, SPA) with live reload; Ctrl+C stops it
dev:
    docker compose up --build

# Start the database only, detached, and wait until it is healthy
db:
    docker compose up -d --wait db

# Run the database tests (starts the database when needed)
test-db:
    uv run --no-project python .claude/skills/test/scripts/run_tests.py . db

# Regenerate the SPA's API client from the backend's OpenAPI schema
api-client:
    uv run --no-project python scripts/api_client.py . generate

# Run every static check (read-only): ruff, pyright, ESLint, tsc, Prettier, client freshness, doc checkers, openspec, hygiene hooks
check:
    uv run --no-project python scripts/run_checks.py

# Format and auto-fix the code (harness, backend, frontend)
format:
    uv run ruff format
    uv run ruff check --fix
    uv run --directory backend ruff format .
    uv run --directory backend ruff check --fix .
    pnpm --dir frontend format

# Run the unit tests
test:
    uv run --no-project python .claude/skills/test/scripts/run_tests.py . unit

# Run all tests, including the database suite
test-all:
    uv run --no-project python .claude/skills/test/scripts/run_tests.py . all
