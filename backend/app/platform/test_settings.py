"""Unit tests of the settings."""

import pytest
from pydantic import ValidationError

from app.platform.settings import Settings

URL = "postgresql+psycopg://u:p@localhost:5432/db"


def test_settings_reads_database_url_from_the_environment(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("DATABASE_URL", URL)

    settings = Settings(_env_file=None)  # pyright: ignore[reportCallIssue] -- required field comes from env

    assert settings.database_url == URL


def test_settings_fails_loudly_when_database_url_is_missing(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("DATABASE_URL", raising=False)

    with pytest.raises(ValidationError, match="database_url"):
        Settings(_env_file=None)  # pyright: ignore[reportCallIssue] -- required field is missing on purpose
