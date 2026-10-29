"""One-time tokens: random values go out in links, only their hashes are stored."""

import hashlib
import secrets

TOKEN_BYTES = 32


def new_token() -> str:
    """A random URL-safe token of 32 bytes."""
    return secrets.token_urlsafe(TOKEN_BYTES)


def hash_token(token: str) -> str:
    """The SHA-256 hex digest that is stored instead of the token."""
    return hashlib.sha256(token.encode("utf-8")).hexdigest()
