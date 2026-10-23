"""Unit tests of the health use case, with a fake repository."""

import asyncio

import pytest

from app.modules.health.service import get_health_status

SHORT_TIMEOUT = 0.05


class FakeRepository:
    """Ping that returns, raises or hangs."""

    def __init__(self, *, fail: bool = False, hang: bool = False) -> None:
        self._fail = fail
        self._hang = hang

    async def ping(self) -> None:
        """Raise, hang for 10 seconds, or return, as built."""
        if self._fail:
            raise ConnectionError("down")
        if self._hang:
            await asyncio.sleep(10)


async def test_database_is_ok_when_ping_returns() -> None:
    result = await get_health_status(FakeRepository())

    assert result.model_dump() == {"status": "ok", "database": "ok"}


async def test_database_is_unavailable_when_ping_raises(caplog: pytest.LogCaptureFixture) -> None:
    result = await get_health_status(FakeRepository(fail=True))

    assert result.model_dump() == {"status": "ok", "database": "unavailable"}
    assert "database ping failed" in caplog.text


async def test_database_is_unavailable_when_ping_times_out() -> None:
    result = await get_health_status(FakeRepository(hang=True), timeout_seconds=SHORT_TIMEOUT)

    assert result.model_dump() == {"status": "ok", "database": "unavailable"}
