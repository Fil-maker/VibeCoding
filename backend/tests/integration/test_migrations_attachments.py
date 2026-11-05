"""Migration 0009 (change 1-11): `emails.attachment_names` becomes `emails.attachments`."""

from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any
from uuid import uuid4

import pytest
from alembic import command
from sqlalchemy import create_engine, inspect, text

from tests.alembic_runner import alembic_config, current_revision, upgrade_to_head
from tests.database_settings import TestDatabaseSettings

MOMENT = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
USER_ID = uuid4()
CHAIN_ID = uuid4()


def _insert_old_emails(url: str) -> None:
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            conn.execute(text("TRUNCATE users CASCADE"))  # leftovers of other tests
            conn.execute(
                text(
                    "INSERT INTO users (id, email, name, password_hash, confirmed_at, created_at) "
                    "VALUES (:id, 'anna@romashka.test', 'Анна', 'x', :moment, :moment)"
                ),
                {"id": USER_ID, "moment": MOMENT},
            )
            conn.execute(
                text(
                    "INSERT INTO reply_chains (id, user_id, latest_email_at, created_at) "
                    "VALUES (:id, :user, :moment, :moment)"
                ),
                {"id": CHAIN_ID, "user": USER_ID, "moment": MOMENT},
            )
            for key, names in (("old-1", ["акт.pdf", "акт.pdf"]), ("old-2", [])):
                conn.execute(
                    text(
                        'INSERT INTO emails (id, user_id, chain_id, key, message_id, "references", '
                        "subject, from_address, to_addresses, cc_addresses, sent_at, text, "
                        "attachment_names, created_at) VALUES (:id, :user, :chain, :key, :key, "
                        "'{}', 'Акт', 'oleg@stroy.test', '[]', '[]', :moment, 'Текст', :names, "
                        ":moment)"
                    ),
                    {
                        "id": uuid4(),
                        "user": USER_ID,
                        "chain": CHAIN_ID,
                        "key": key,
                        "moment": MOMENT,
                        "names": names,
                    },
                )
    finally:
        engine.dispose()


def _attachments(url: str) -> dict[str, Any]:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT key, attachments FROM emails")).all()
            return {key: value for key, value in rows}
    finally:
        engine.dispose()


@pytest.fixture
def emails_at_0008() -> Iterator[str]:
    """The test database at 0008 with two emails stored the old way; back to head and empty."""
    url = TestDatabaseSettings().test_database_url  # pyright: ignore[reportCallIssue] -- filled from env
    try:
        upgrade_to_head(url)
        with alembic_config(url) as config:
            command.downgrade(config, "0008")
        assert current_revision(url) == "0008"
        _insert_old_emails(url)
        yield url
    finally:
        with alembic_config(url) as config:
            command.downgrade(config, "0001")  # drops the data with the tables
        upgrade_to_head(url)


def test_fr31_an_email_read_before_sizes_were_kept_gets_its_names_with_null_sizes(
    emails_at_0008: str,
) -> None:
    # FR-31 «An attachment read before sizes were kept»
    upgrade_to_head(emails_at_0008)

    stored = _attachments(emails_at_0008)

    assert stored["old-1"] == [
        {"name": "акт.pdf", "size": None},
        {"name": "акт.pdf", "size": None},
    ]
    assert stored["old-2"] == []


def test_downgrade_of_0009_restores_the_names_and_drops_the_sizes(emails_at_0008: str) -> None:
    # design «Data and migration»: downgrade rebuilds attachment_names from the names
    upgrade_to_head(emails_at_0008)
    assert _attachments(emails_at_0008)["old-1"] == [
        {"name": "акт.pdf", "size": None},
        {"name": "акт.pdf", "size": None},
    ]
    with alembic_config(emails_at_0008) as config:
        command.downgrade(config, "0008")

    engine = create_engine(emails_at_0008)
    try:
        with engine.connect() as conn:
            rows = conn.execute(text("SELECT key, attachment_names FROM emails")).all()
    finally:
        engine.dispose()
    assert {key: names for key, names in rows} == {"old-1": ["акт.pdf", "акт.pdf"], "old-2": []}
    engine = create_engine(emails_at_0008)
    try:
        with engine.connect() as conn:
            columns = {c["name"] for c in inspect(conn).get_columns("emails")}
    finally:
        engine.dispose()
    assert "attachments" not in columns
