"""The application factory."""

import asyncio
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager, suppress

from fastapi import FastAPI

from app.modules.accounts.router import ERROR_MAPPING as ACCOUNTS_ERRORS
from app.modules.accounts.router import router as accounts_router
from app.modules.auth.router import ERROR_MAPPING as AUTH_ERRORS
from app.modules.auth.router import router as auth_router
from app.modules.correspondence.router import ERROR_MAPPING as CORRESPONDENCE_ERRORS
from app.modules.correspondence.router import router as correspondence_router
from app.modules.health.router import router as health_router
from app.modules.mailboxes.router import register_mailbox_errors
from app.modules.mailboxes.router import router as mailboxes_router
from app.modules.mailboxes.service import run_reading_loop
from app.platform.clock import get_clock
from app.platform.db import Database
from app.platform.errors import register_domain_errors, register_error_handlers
from app.platform.logging import configure_logging
from app.platform.mail_reader import ImapMailReader, MailReader
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
    async def lifespan(app_: FastAPI) -> AsyncGenerator[None]:
        loop_task: asyncio.Task[None] | None = None
        if resolved.mailbox_reading_enabled:
            reader: MailReader | None = app_.state.mail_reader
            if reader is None:
                reader = ImapMailReader(timeout=resolved.imap_timeout_seconds)
                app_.state.mail_reader = reader
            loop_task = asyncio.create_task(
                run_reading_loop(database, reader, get_clock(), resolved)
            )
        try:
            yield
        finally:
            if loop_task is not None:
                loop_task.cancel()
                with suppress(asyncio.CancelledError):
                    await loop_task
            await database.dispose()

    app = FastAPI(title="VibeCoding", lifespan=lifespan)
    app.state.database = database
    app.state.settings = resolved
    app.state.mail_sender = None  # created lazily by `get_mail_sender`
    app.state.mail_reader = None  # created lazily by `get_mail_reader`
    app.state.secret_box = None  # created lazily by `get_secret_box`
    register_error_handlers(app)
    register_domain_errors(app, ACCOUNTS_ERRORS)
    register_domain_errors(app, AUTH_ERRORS)
    register_domain_errors(app, CORRESPONDENCE_ERRORS)
    register_mailbox_errors(app)
    app.add_middleware(OriginGuardMiddleware, app_base_url=resolved.app_base_url)
    app.include_router(health_router)
    app.include_router(accounts_router)
    app.include_router(auth_router)
    app.include_router(mailboxes_router)
    app.include_router(correspondence_router)
    return app
