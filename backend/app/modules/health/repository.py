"""The database ping."""

from typing import Annotated, Protocol

from fastapi import Depends
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

from app.platform.db import get_database_session


class HealthRepository(Protocol):
    """What the service needs from the database."""

    async def ping(self) -> None:
        """Return when the database answers; raise otherwise."""
        ...


class SqlHealthRepository:
    """`SELECT 1` through a session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def ping(self) -> None:
        """Run `SELECT 1`."""
        await self._session.execute(text("SELECT 1"))


def get_health_repository(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> HealthRepository:
    """Dependency factory; tests override it with a fake."""
    return SqlHealthRepository(session)
