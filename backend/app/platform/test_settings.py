"""Unit tests of the settings."""

import pytest
from pydantic import ValidationError

from app.platform.settings import Settings

URL = "postgresql+psycopg://u:p@localhost:5432/db"
REQUIRED = {
    "DATABASE_URL": URL,
    "APP_BASE_URL": "http://localhost:5173",
    "MAIL_FROM": "noreply@vibecoding.test",
    "SMTP_HOST": "mailpit",
}
OPTIONAL = [
    "SMTP_PORT",
    "SMTP_USERNAME",
    "SMTP_PASSWORD",
    "SMTP_STARTTLS",
    "SESSION_COOKIE_SECURE",
    "SESSION_LIFETIME_DAYS",
    "CONFIRMATION_LINK_HOURS",
    "PASSWORD_RESET_LINK_MINUTES",
    "INVITATION_LIFETIME_DAYS",
    "SIGN_IN_MAX_FAILURES",
    "SIGN_IN_FAILURE_WINDOW_MINUTES",
    "SIGN_IN_LOCK_MINUTES",
]


def build_settings() -> Settings:
    """Settings from the environment only, never from `.env`."""
    return Settings(_env_file=None)  # pyright: ignore[reportCallIssue] -- required fields come from env


@pytest.fixture
def required_env(monkeypatch: pytest.MonkeyPatch) -> pytest.MonkeyPatch:
    """The required variables set and every optional one removed."""
    for name, value in REQUIRED.items():
        monkeypatch.setenv(name, value)
    for name in OPTIONAL:
        monkeypatch.delenv(name, raising=False)
    return monkeypatch


def test_settings_reads_database_url_from_the_environment(required_env: pytest.MonkeyPatch) -> None:
    assert build_settings().database_url == URL


def test_settings_reads_the_required_mail_and_link_values(required_env: pytest.MonkeyPatch) -> None:
    settings = build_settings()

    assert settings.app_base_url == "http://localhost:5173"
    assert settings.mail_from == "noreply@vibecoding.test"
    assert settings.smtp_host == "mailpit"


@pytest.mark.parametrize("missing", ["DATABASE_URL", "APP_BASE_URL", "MAIL_FROM", "SMTP_HOST"])
def test_settings_fails_loudly_when_a_required_value_is_missing(
    required_env: pytest.MonkeyPatch, missing: str
) -> None:
    required_env.delenv(missing)

    with pytest.raises(ValidationError, match=missing.lower()):
        build_settings()


def test_settings_defaults_of_the_mail_and_cookie_fields(required_env: pytest.MonkeyPatch) -> None:
    settings = build_settings()

    assert settings.smtp_port == 1025
    assert settings.smtp_username is None
    assert settings.smtp_password is None
    assert settings.smtp_starttls is False
    assert settings.session_cookie_secure is False


def test_settings_defaults_of_the_lifetimes_and_limits(required_env: pytest.MonkeyPatch) -> None:
    settings = build_settings()

    assert settings.session_lifetime_days == 14
    assert settings.confirmation_link_hours == 24
    assert settings.password_reset_link_minutes == 60
    assert settings.invitation_lifetime_days == 7
    assert settings.sign_in_max_failures == 5
    assert settings.sign_in_failure_window_minutes == 15
    assert settings.sign_in_lock_minutes == 15
