"""Unit tests of the password hasher."""

from argon2 import PasswordHasher

from app.platform.passwords import hash_password, verify_password

PASSWORD = "correct-horse-1"


async def test_hash_is_not_the_password_and_differs_between_calls() -> None:
    first = await hash_password(PASSWORD)
    second = await hash_password(PASSWORD)

    assert PASSWORD not in first
    assert first.startswith("$argon2id$")
    assert first != second


async def test_a_hash_verifies_the_password_it_was_made_from() -> None:
    password_hash = await hash_password(PASSWORD)

    check = await verify_password(password_hash, PASSWORD)

    assert check.ok is True
    assert check.needs_rehash is False


async def test_a_wrong_password_does_not_verify() -> None:
    password_hash = await hash_password(PASSWORD)

    check = await verify_password(password_hash, "wrong-horse-1")

    assert check.ok is False


async def test_no_hash_gives_not_ok() -> None:
    check = await verify_password(None, PASSWORD)

    assert check.ok is False


async def test_a_hash_with_weaker_parameters_verifies_and_needs_rehash() -> None:
    weak = PasswordHasher(time_cost=1, memory_cost=8, parallelism=1).hash(PASSWORD)

    check = await verify_password(weak, PASSWORD)

    assert check.ok is True
    assert check.needs_rehash is True
