"""The injected clock: time is a parameter, never read inside the code that decides."""

from datetime import UTC, datetime
from typing import Protocol


class Clock(Protocol):
    """Source of the current time."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC time."""
        ...


class SystemClock:
    """The real clock."""

    def now(self) -> datetime:
        """Return the current timezone-aware UTC time."""
        return datetime.now(UTC)
