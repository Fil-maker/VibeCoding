# Dev image of the backend: Python 3.12 and uv. The code and the virtualenv are mounted by compose.
FROM python:3.12-slim

COPY --from=ghcr.io/astral-sh/uv:0.9.3 /uv /usr/local/bin/uv

ENV UV_PROJECT_ENVIRONMENT=/opt/venv \
    UV_LINK_MODE=copy \
    PATH=/opt/venv/bin:$PATH

WORKDIR /app/backend

# Bake the locked dependencies; the named venv volume starts from them,
# and the compose command re-syncs it at every start, so later dependencies arrive too.
COPY backend/pyproject.toml backend/uv.lock ./
RUN uv sync --frozen --no-install-project
