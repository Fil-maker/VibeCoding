"""Fixtures of the integration suite: the real PostgreSQL behind TEST_DATABASE_URL."""

import asyncio
from collections.abc import AsyncIterator, Callable, Mapping

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic_settings import BaseSettings, SettingsConfigDict

from app.main import create_app
from app.platform.settings import REPO_ENV_FILE, Settings


class TestDatabaseSettings(BaseSettings):
    """The test database URL; tests never read the dev DATABASE_URL."""

    __test__ = False
    model_config = SettingsConfigDict(env_file=REPO_ENV_FILE, extra="ignore")

    test_database_url: str


def pytest_asyncio_loop_factories(
    config: pytest.Config, item: pytest.Item
) -> Mapping[str, Callable[[], asyncio.AbstractEventLoop]]:
    """psycopg async cannot run on the Windows default Proactor loop."""
    return {"selector": asyncio.SelectorEventLoop}


@pytest.fixture
def test_database_url() -> str:
    """The test database URL from TEST_DATABASE_URL; the dev DATABASE_URL is never read."""
    return TestDatabaseSettings().test_database_url  # pyright: ignore[reportCallIssue] -- filled from env


@pytest.fixture
def app(test_database_url: str) -> FastAPI:
    """The app wired to the test database."""
    return create_app(Settings(database_url=test_database_url))


@pytest.fixture
async def client(app: FastAPI) -> AsyncIterator[AsyncClient]:
    """An HTTP client that runs the app's lifespan; requests stay in-process, no port opens."""
    async with (
        app.router.lifespan_context(app),
        AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as http,
    ):
        yield http
