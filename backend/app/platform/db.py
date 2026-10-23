"""The database client: one lazy async engine and session factory per process."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import Request
from sqlalchemy import MetaData
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base of every module's models."""

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class Database:
    """Owns the engine; it is created on first use, never at import."""

    def __init__(self, url: str) -> None:
        self._url = url
        self._engine: AsyncEngine | None = None
        self._sessions: async_sessionmaker[AsyncSession] | None = None

    @property
    def engine(self) -> AsyncEngine:
        """The engine, created on first access."""
        if self._engine is None:
            self._engine = create_async_engine(self._url)
        return self._engine

    @asynccontextmanager
    async def session(self) -> AsyncGenerator[AsyncSession]:
        """Open a session; the service decides when to begin a transaction."""
        if self._sessions is None:
            self._sessions = async_sessionmaker(self.engine, expire_on_commit=False)
        async with self._sessions() as session:
            yield session

    async def dispose(self) -> None:
        """Close the pool; a never-used engine is skipped."""
        if self._engine is not None:
            await self._engine.dispose()


async def get_database_session(request: Request) -> AsyncGenerator[AsyncSession]:
    """Dependency: a session from the app's database; closed when the request ends."""
    database: Database = request.app.state.database
    async with database.session() as session:
        yield session
