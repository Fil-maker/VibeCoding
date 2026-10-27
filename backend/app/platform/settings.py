"""Application settings: the app's only reader of the environment and of `.env`.

The integration tests read `TEST_DATABASE_URL` in their own conftest, not here.
"""

from pathlib import Path

from fastapi import Request
from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Typed settings from the environment and `.env`; a missing required value raises on build."""

    model_config = SettingsConfigDict(env_file=REPO_ENV_FILE, extra="ignore")

    database_url: str

    # Links in emails and the Origin check.
    app_base_url: str
    mail_from: str
    smtp_host: str
    smtp_port: int = 1025
    smtp_username: str | None = None
    smtp_password: str | None = None
    smtp_starttls: bool = False

    session_cookie_secure: bool = False
    session_lifetime_days: int = 14
    confirmation_link_hours: int = 24
    password_reset_link_minutes: int = 60
    invitation_lifetime_days: int = 7

    sign_in_max_failures: int = 5
    sign_in_failure_window_minutes: int = 15
    sign_in_lock_minutes: int = 15


def get_settings(request: Request) -> Settings:
    """Dependency: the settings the app was built with."""
    settings: Settings = request.app.state.settings
    return settings
