"""Encryption of mailbox passwords with a Fernet key from the settings."""

from typing import Annotated

from cryptography.fernet import Fernet, InvalidToken
from fastapi import Depends, Request

from app.platform.settings import Settings, get_settings


class SecretBoxError(Exception):
    """The ciphertext cannot be opened: a wrong key or damaged data."""


class SecretBox:
    """Encrypts short secrets; the plaintext lives only in memory."""

    def __init__(self, key: str) -> None:
        try:
            self._fernet = Fernet(key.encode("ascii"))
        except (ValueError, UnicodeEncodeError) as e:
            raise SecretBoxError("the encryption key is not a valid Fernet key") from e

    def encrypt(self, plaintext: str) -> bytes:
        """The ciphertext of the text."""
        return self._fernet.encrypt(plaintext.encode("utf-8"))

    def decrypt(self, ciphertext: bytes) -> str:
        """The text of a ciphertext made with this key; `SecretBoxError` otherwise."""
        try:
            return self._fernet.decrypt(ciphertext).decode("utf-8")
        except (InvalidToken, UnicodeDecodeError) as e:
            raise SecretBoxError("the ciphertext cannot be opened with this key") from e


def get_secret_box(
    request: Request, settings: Annotated[Settings, Depends(get_settings)]
) -> SecretBox:
    """Dependency: the app's box, created on first use from the settings."""
    box: SecretBox | None = getattr(request.app.state, "secret_box", None)
    if box is None:
        box = SecretBox(settings.mailbox_encryption_key)
        request.app.state.secret_box = box
    return box
