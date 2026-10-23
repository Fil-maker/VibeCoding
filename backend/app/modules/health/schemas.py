"""Response models of the health module."""

from typing import Literal

from pydantic import BaseModel

DatabaseState = Literal["ok", "unavailable"]


class HealthStatus(BaseModel):
    """The state of the service and its database."""

    status: Literal["ok"]
    database: DatabaseState
