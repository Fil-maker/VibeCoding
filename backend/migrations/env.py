"""Alembic environment: async engine, URL from the application settings."""

import asyncio
import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import create_async_engine

from app.main import load_settings
from app.modules.accounts.models import Organization, User
from app.modules.auth.models import SignInFailure, UserSession, UserToken
from app.modules.invitations.models import Invitation
from app.platform.db import Base

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Importing the models registers their tables on the metadata; the tuple keeps the imports used.
MODELS = (Organization, User, UserSession, UserToken, SignInFailure, Invitation)
target_metadata = Base.metadata
LOG = logging.getLogger("alembic.env")


def run_migrations_offline() -> None:
    """Emit SQL without a connection."""
    context.configure(
        url=load_settings().database_url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    """Run the migrations on a synchronous connection facade."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    """Run the migrations through an async engine."""
    engine = create_async_engine(load_settings().database_url)
    async with engine.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await engine.dispose()


def run_online() -> None:
    """Run online migrations; psycopg needs the selector loop, not Windows' Proactor default."""
    with asyncio.Runner(loop_factory=asyncio.SelectorEventLoop) as runner:
        runner.run(run_migrations_online())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_online()
