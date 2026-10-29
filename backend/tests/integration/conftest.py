"""Fixtures of the integration suite: the real PostgreSQL behind TEST_DATABASE_URL."""

import asyncio
from collections.abc import AsyncIterator, Callable, Mapping

import pytest
from fastapi import FastAPI
from httpx import AsyncClient
from sqlalchemy import create_engine, text

from app.main import create_app
from app.platform.clock import get_clock
from app.platform.mail import FakeMailSender, get_mail_sender
from app.platform.mail_reader import FakeMailReader, get_mail_reader
from tests.alembic_runner import upgrade_to_head
from tests.database_settings import TestDatabaseSettings
from tests.factories import Factories, settings_for
from tests.settable_clock import CLOCK_START, SettableClock


def pytest_asyncio_loop_factories(
    config: pytest.Config, item: pytest.Item
) -> Mapping[str, Callable[[], asyncio.AbstractEventLoop]]:
    """psycopg async cannot run on the Windows default Proactor loop."""
    return {"selector": asyncio.SelectorEventLoop}


@pytest.fixture(scope="session")
def migrated_database_url() -> str:
    """The test database at the head revision."""
    url = TestDatabaseSettings().test_database_url  # pyright: ignore[reportCallIssue] -- filled from env
    upgrade_to_head(url)
    return url


@pytest.fixture
def test_database_url(migrated_database_url: str) -> str:
    """The test database URL from TEST_DATABASE_URL, emptied of data; the dev URL is never read."""
    engine = create_engine(migrated_database_url)
    with engine.begin() as connection:
        names = (
            connection.execute(
                text(
                    "SELECT tablename FROM pg_tables "
                    "WHERE schemaname = 'public' AND tablename <> 'alembic_version'"
                )
            )
            .scalars()
            .all()
        )
        if names:
            connection.execute(text("TRUNCATE " + ", ".join(f'"{n}"' for n in names) + " CASCADE"))
    engine.dispose()
    return migrated_database_url


@pytest.fixture
def mail() -> FakeMailSender:
    """The fake mail sender the app of a test uses."""
    return FakeMailSender()


@pytest.fixture
def clock() -> SettableClock:
    """The clock of the test; it moves only when the test advances it."""
    return SettableClock(CLOCK_START)


@pytest.fixture
def reader() -> FakeMailReader:
    """The fake mailbox reader: the mailboxes of the test live in it."""
    return FakeMailReader()


@pytest.fixture
def app(
    test_database_url: str, mail: FakeMailSender, clock: SettableClock, reader: FakeMailReader
) -> FastAPI:
    """The app wired to the test database, with the fake mail sender and the settable clock."""
    application = create_app(settings_for(test_database_url))
    application.dependency_overrides[get_mail_sender] = lambda: mail
    application.dependency_overrides[get_mail_reader] = lambda: reader
    application.dependency_overrides[get_clock] = lambda: clock
    return application


@pytest.fixture
async def factories(
    app: FastAPI, mail: FakeMailSender, clock: SettableClock, reader: FakeMailReader
) -> AsyncIterator[Factories]:
    """Factories and clients over the running app; requests stay in-process, no port opens."""
    built = Factories(app, mail, clock, reader)
    async with app.router.lifespan_context(app):
        yield built
        await built.close()


@pytest.fixture
async def client(factories: Factories) -> AsyncClient:
    """A client without a session whose requests carry the right Origin."""
    return await factories.open_client()
