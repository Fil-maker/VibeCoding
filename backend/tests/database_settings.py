"""The test database URL; tests never read the dev DATABASE_URL."""

from pydantic_settings import BaseSettings, SettingsConfigDict

from app.platform.settings import REPO_ENV_FILE


class TestDatabaseSettings(BaseSettings):
    """Reads TEST_DATABASE_URL from the environment or `.env`."""

    __test__ = False
    model_config = SettingsConfigDict(env_file=REPO_ENV_FILE, extra="ignore")

    test_database_url: str
