"""HTTP entry of the health module."""

from typing import Annotated

from fastapi import APIRouter, Depends

from app.modules.health.repository import HealthRepository, get_health_repository
from app.modules.health.schemas import HealthStatus
from app.modules.health.service import get_health_status

router = APIRouter(prefix="/api/v1", tags=["health"])


@router.get("/health", response_model=HealthStatus, status_code=200)
async def read_health(
    repository: Annotated[HealthRepository, Depends(get_health_repository)],
) -> HealthStatus:
    """Report the service and database state."""
    return await get_health_status(repository)
