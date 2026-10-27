"""The application factory."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from app.modules.accounts.router import ERROR_MAPPING as ACCOUNTS_ERRORS
from app.modules.accounts.router import members_router
from app.modules.accounts.router import router as accounts_router
from app.modules.auth.router import ERROR_MAPPING as AUTH_ERRORS
from app.modules.auth.router import router as auth_router
from app.modules.health.router import router as health_router
from app.modules.invitations.router import ERROR_MAPPING as INVITATIONS_ERRORS
from app.modules.invitations.router import router as invitations_router
from app.platform.db import Database
from app.platform.errors import register_domain_errors, register_error_handlers
from app.platform.logging import configure_logging
from app.platform.origin import OriginGuardMiddleware
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
    app.state.settings = resolved
    app.state.mail_sender = None  # created lazily by `get_mail_sender`
    register_error_handlers(app)
    register_domain_errors(app, ACCOUNTS_ERRORS)
    register_domain_errors(app, AUTH_ERRORS)
    register_domain_errors(app, INVITATIONS_ERRORS)
    app.add_middleware(OriginGuardMiddleware, app_base_url=resolved.app_base_url)
    app.include_router(health_router)
    app.include_router(accounts_router)
    app.include_router(members_router)
    app.include_router(auth_router)
    app.include_router(invitations_router)
    return app
