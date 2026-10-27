"""Run Alembic through its Python API against the test database."""

import os
from collections.abc import Generator
from contextlib import contextmanager
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.runtime.migration import MigrationContext
from sqlalchemy import create_engine

BACKEND_DIR = Path(__file__).resolve().parents[1]
ENV_FOR_SETTINGS = {
    "APP_BASE_URL": "http://localhost:5173",
    "MAIL_FROM": "noreply@vibecoding.test",
    "SMTP_HOST": "localhost",
}


@contextmanager
def alembic_config(database_url: str) -> Generator[Config]:
    """A config whose env.py sees the test database; the environment is restored afterwards."""
    values = {"DATABASE_URL": database_url, **ENV_FOR_SETTINGS}
    saved = {key: os.environ.get(key) for key in values}
    os.environ.update(values)
    try:
        yield Config(str(BACKEND_DIR / "alembic.ini"))
    finally:
        for key, old in saved.items():
            if old is None:
                os.environ.pop(key, None)
            else:
                os.environ[key] = old


def upgrade_to_head(database_url: str) -> None:
    """Upgrade the test database to the head revision."""
    with alembic_config(database_url) as config:
        command.upgrade(config, "head")


def current_revision(database_url: str) -> str | None:
    """The revision recorded in the test database."""
    engine = create_engine(database_url)
    try:
        with engine.connect() as connection:
            return MigrationContext.configure(connection).get_current_revision()
    finally:
        engine.dispose()
