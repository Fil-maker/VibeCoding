"""The health use case."""

import asyncio

from app.modules.health.repository import HealthRepository
from app.modules.health.schemas import DatabaseState, HealthStatus
from app.platform.logging import get_logger

PING_TIMEOUT_SECONDS = 2.0

LOG = get_logger(__name__)


async def get_health_status(
    repository: HealthRepository, timeout_seconds: float = PING_TIMEOUT_SECONDS
) -> HealthStatus:
    """Ping the database; a failure or a timeout is reported, never raised."""
    database: DatabaseState = "ok"
    try:
        async with asyncio.timeout(timeout_seconds):
            await repository.ping()
    except Exception:  # the endpoint must answer whatever the driver raises
        LOG.exception("database ping failed")
        database = "unavailable"
    return HealthStatus(status="ok", database=database)
