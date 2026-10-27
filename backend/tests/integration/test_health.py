"""Integration tests of GET /api/v1/health against the test database."""

from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from app.main import create_app
from app.platform.settings import Settings


async def test_health_reports_database_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}


async def test_health_reports_unavailable_when_the_database_is_unreachable() -> None:
    unreachable = "postgresql+psycopg://u:p@127.0.0.1:1/none?connect_timeout=1"
    app: FastAPI = create_app(
        Settings(
            database_url=unreachable,
            app_base_url="http://localhost:5173",
            mail_from="noreply@vibecoding.test",
            smtp_host="localhost",
        )
    )

    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client,
    ):
        response = await client.get("/api/v1/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "unavailable"}
