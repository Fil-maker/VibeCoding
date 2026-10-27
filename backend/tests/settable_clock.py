"""A clock that tests move by hand; no sleeps."""

from datetime import UTC, datetime, timedelta


class SettableClock:
    """Implements `app.platform.clock.Clock`; time stands still until a test advances it."""

    def __init__(self, start: datetime) -> None:
        self._now = start

    def now(self) -> datetime:
        """Return the current fake time."""
        return self._now

    def advance(self, delta: timedelta) -> None:
        """Move the time forward."""
        self._now += delta


# Far in the future so a cookie dated by this clock is never already expired for the HTTP client.
CLOCK_START = datetime(2099, 1, 1, 12, 0, tzinfo=UTC)
