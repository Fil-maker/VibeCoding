"""Password hashing: Argon2id with default parameters, run in a worker thread."""

from dataclasses import dataclass
from functools import cache

import anyio.to_thread
from argon2 import PasswordHasher
from argon2.exceptions import InvalidHashError, VerificationError

_HASHER = PasswordHasher()
_DUMMY_PASSWORD = "dummy-password-for-constant-time"


@dataclass(frozen=True)
class PasswordCheck:
    """The outcome of a verification."""

    ok: bool
    needs_rehash: bool


@cache
def _dummy_hash() -> str:
    return _HASHER.hash(_DUMMY_PASSWORD)


def _verify(password_hash: str, password: str) -> PasswordCheck:
    try:
        _HASHER.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return PasswordCheck(ok=False, needs_rehash=False)
    return PasswordCheck(ok=True, needs_rehash=_HASHER.check_needs_rehash(password_hash))


async def hash_password(password: str) -> str:
    """Hash a password; the work runs in a worker thread."""
    return await anyio.to_thread.run_sync(_HASHER.hash, password)


async def verify_password(password_hash: str | None, password: str) -> PasswordCheck:
    """Check a password; `None` (unknown user) verifies against a dummy hash and fails."""
    if password_hash is None:
        await anyio.to_thread.run_sync(_verify, _dummy_hash(), password)
        return PasswordCheck(ok=False, needs_rehash=False)
    return await anyio.to_thread.run_sync(_verify, password_hash, password)
