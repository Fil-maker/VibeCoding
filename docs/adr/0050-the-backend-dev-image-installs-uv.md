# The backend dev image installs uv 0.9.3 from PyPI (pip install) instead of copying it from the ghcr.io/astral-sh/uv image

Id: 0050 · Date: 29.10.2026 · Kind: technical · Status: Accepted · Who: [human]

## Context
Task: fix-uv-from-pypi.
- docker/backend.Dockerfile installs uv with RUN pip install --no-cache-dir uv==0.9.3 from PyPI; the image build no longer pulls ghcr.io/astral-sh/uv. The pin stays 0.9.3.

## Decision
The backend dev image installs uv 0.9.3 from PyPI (pip install) instead of copying it from the ghcr.io/astral-sh/uv image

## Alternatives
keep COPY --from=ghcr.io/astral-sh/uv:0.9.3

## Reason
Пользователь выбрал «Перейти на PyPI» после того, как just dev упал на DNS до ghcr.io
