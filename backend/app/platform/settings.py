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

    sign_in_max_failures: int = 5
    sign_in_failure_window_minutes: int = 15
    sign_in_lock_minutes: int = 15

    # Mailboxes: reading in the background (FR-24) and the password box (FR-23).
    mailbox_encryption_key: str
    mailbox_reading_enabled: bool = True
    mailbox_read_interval_minutes: int = 5
    mailbox_read_tick_seconds: int = 10
    mailbox_read_depth_days: int = 365
    imap_timeout_seconds: int = 30
    # Comma-separated hosts reached without TLS (local test servers only).
    imap_insecure_hosts: str = ""

    @property
    def insecure_hosts(self) -> frozenset[str]:
        """The hosts of `imap_insecure_hosts`, trimmed and lower-cased."""
        parts = (part.strip().lower() for part in self.imap_insecure_hosts.split(","))
        return frozenset(part for part in parts if part)


def get_settings(request: Request) -> Settings:
    """Dependency: the settings the app was built with."""
    settings: Settings = request.app.state.settings
    return settings
