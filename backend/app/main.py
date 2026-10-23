"""The application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.modules.health.router import router as health_router
from app.platform.db import Database
from app.platform.logging import configure_logging
from app.platform.settings import Settings


def load_settings() -> Settings:
    """Read the settings from the environment; fails loudly when a value is missing."""
    return Settings()  # pyright: ignore[reportCallIssue] -- pydantic-settings fills fields from env


def create_app(settings: Settings | None = None) -> FastAPI:
    """Build the app; settings come from the environment when not given."""
    configure_logging()
    resolved = settings if settings is not None else load_settings()
    database = Database(resolved.database_url)

    @asynccontextmanager
    async def lifespan(_app: FastAPI) -> AsyncGenerator[None]:
        yield
        await database.dispose()

    app = FastAPI(title="VibeCoding", lifespan=lifespan)
    app.state.database = database
    app.include_router(health_router)
    return app
