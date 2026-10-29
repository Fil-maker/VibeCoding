"""Unit tests of the encryption of mailbox passwords."""

import base64

import pytest

from app.platform.secret_box import SecretBox

KEY = base64.urlsafe_b64encode(b"0" * 32).decode()
OTHER_KEY = base64.urlsafe_b64encode(b"1" * 32).decode()


def test_a_secret_survives_a_round_trip() -> None:
    box = SecretBox(KEY)

    assert box.decrypt(box.encrypt("app-pass-1234")) == "app-pass-1234"


def test_the_ciphertext_does_not_contain_the_secret() -> None:
    encrypted = SecretBox(KEY).encrypt("app-pass-1234")

    assert isinstance(encrypted, bytes)
    assert b"app-pass-1234" not in encrypted


def test_a_non_ascii_secret_survives_a_round_trip() -> None:
    box = SecretBox(KEY)

    assert box.decrypt(box.encrypt("пароль-приложения")) == "пароль-приложения"


def test_a_wrong_key_does_not_decrypt() -> None:
    encrypted = SecretBox(KEY).encrypt("app-pass-1234")

    # the Interface names no error type, only that decrypting with another key is refused
    with pytest.raises(Exception) as refused:
        SecretBox(OTHER_KEY).decrypt(encrypted)

    assert "app-pass-1234" not in str(refused.value)


def test_a_tampered_ciphertext_does_not_decrypt() -> None:
    box = SecretBox(KEY)
    encrypted = bytearray(box.encrypt("app-pass-1234"))
    encrypted[-3] ^= 0x01

    with pytest.raises(Exception):  # noqa: B017 -- error type is not in the Interface
        box.decrypt(bytes(encrypted))
