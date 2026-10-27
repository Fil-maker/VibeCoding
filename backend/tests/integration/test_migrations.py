"""Integration test of the migrations on the test database; sync, Alembic runs its own loop."""

from alembic import command
from alembic.script import ScriptDirectory

from tests.alembic_runner import alembic_config, current_revision, upgrade_to_head
from tests.database_settings import TestDatabaseSettings


def test_migrations_round_trip_leaves_no_drift() -> None:
    url = TestDatabaseSettings().test_database_url  # pyright: ignore[reportCallIssue] -- filled from env

    upgrade_to_head(url)
    with alembic_config(url) as config:
        head = ScriptDirectory.from_config(config).get_current_head()
        assert current_revision(url) == head
        command.downgrade(config, "0001")
        assert current_revision(url) == "0001"
        command.upgrade(config, "head")
        assert current_revision(url) == head
        command.check(config)  # raises when the models and the migrations differ
