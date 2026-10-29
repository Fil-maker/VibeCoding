"""Pure rules of the sign-in lock."""

from collections.abc import Sequence
from datetime import datetime, timedelta


def is_locked(
    failures: Sequence[datetime],
    now: datetime,
    *,
    max_failures: int,
    window: timedelta,
    lock: timedelta,
) -> bool:
    """Whether sign-in is refused.

    A lock begins at the last failure of a group of `max_failures` failures within `window` and
    lasts `lock`. Refused attempts are not recorded, so the lock never extends itself.
    """
    ordered = sorted(failures)
    for index, last in enumerate(ordered):
        if now >= last + lock:
            continue
        in_window = [f for f in ordered[: index + 1] if f > last - window]
        if len(in_window) >= max_failures:
            return True
    return False
