"""Unit tests of the health route, with a fake repository."""

import asyncio
from collections.abc import AsyncIterator

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.modules.health.repository import HealthRepository, get_health_repository
from app.platform.settings import Settings


class FakeRepository:
    """Ping that returns or raises."""

    def __init__(self, *, fail: bool = False) -> None:
        self._fail = fail

    async def ping(self) -> None:
        """Return, or raise `ConnectionError` when built with `fail=True`."""
        await asyncio.sleep(0)
        if self._fail:
            raise ConnectionError("down")


def build_app(repository: HealthRepository) -> FastAPI:
    """Build the app with `get_health_repository` overridden to yield `repository`; no database."""
    app = create_app(Settings(database_url="postgresql+psycopg://u:p@localhost/db"))

    async def fake() -> AsyncIterator[HealthRepository]:
        """Yield the fake repository in place of the SQL one."""
        yield repository

    app.dependency_overrides[get_health_repository] = fake
    return app


async def test_route_answers_200_with_unavailable_when_ping_raises() -> None:
    app = build_app(FakeRepository(fail=True))

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "unavailable"}


async def test_route_answers_200_with_ok() -> None:
    app = build_app(FakeRepository())

    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
