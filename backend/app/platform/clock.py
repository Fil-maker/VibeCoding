"""The injected clock: time is a parameter, never read inside the code that decides."""

from datetime import UTC, datetime
from functools import cache
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


@cache
def get_clock() -> Clock:
    """Dependency: the clock, created on first use; tests override it with a settable one."""
    return SystemClock()
