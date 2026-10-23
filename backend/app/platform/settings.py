"""Application settings: the app's only reader of the environment and of `.env`.

The integration tests read `TEST_DATABASE_URL` in their own conftest, not here.
"""

from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

REPO_ENV_FILE = Path(__file__).resolve().parents[3] / ".env"


class Settings(BaseSettings):
    """Typed settings from the environment and `.env`; a missing required value raises on build."""

    model_config = SettingsConfigDict(env_file=REPO_ENV_FILE, extra="ignore")

    database_url: str
