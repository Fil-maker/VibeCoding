"""Integration test of the migrations on the test database; sync, Alembic runs its own loop."""

import asyncio
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from dataclasses import dataclass
from datetime import UTC, datetime
from http import HTTPStatus
from typing import Any
from uuid import UUID, uuid4

import pytest
from alembic import command
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, inspect, text

from app.main import create_app
from app.platform.clock import get_clock
from app.platform.mail import FakeMailSender, get_mail_sender
from app.platform.passwords import hash_password
from tests.alembic_runner import alembic_config, current_revision, upgrade_to_head
from tests.database_settings import TestDatabaseSettings
from tests.factories import Factories, settings_for, sign_in
from tests.settable_clock import SettableClock


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


# --- migration 0003: organizations, roles, deactivation and invitations go away (change 1-1) ---

ADMIN_PASSWORD = "admin-pass-1"
EMPLOYEE_PASSWORD = "employee-pass-1"
DEACTIVATED_PASSWORD = "deactivated-pass-1"
REGISTRANT_PASSWORD = "registrant-pass-1"
USER_COLUMNS = {"id", "email", "name", "password_hash", "confirmed_at", "created_at"}
EXPIRES = datetime(2100, 1, 1, tzinfo=UTC)
CREATED = datetime(2026, 10, 1, 9, 0, tzinfo=UTC)
CONFIRMED = datetime(2026, 10, 2, 9, 0, tzinfo=UTC)


@dataclass(frozen=True)
class LegacyUser:
    """A user as task 0.2 stored it."""

    id: UUID
    email: str
    name: str
    password: str
    password_hash: str
    organization_id: UUID
    role: str
    is_active: bool
    confirmed_at: datetime | None


@dataclass(frozen=True)
class LegacyData:
    """What was inserted at revision 0002."""

    url: str
    users: list[LegacyUser]
    session_user: LegacyUser
    token_user: LegacyUser


def _hash(password: str) -> str:
    """The app's own hashing; a worker thread, as the caller may already run an event loop."""
    with ThreadPoolExecutor(max_workers=1) as pool:
        return pool.submit(lambda: asyncio.run(hash_password(password))).result()


def _user(
    email: str,
    name: str,
    password: str,
    organization_id: UUID,
    *,
    role: str,
    is_active: bool = True,
    confirmed_at: datetime | None = CONFIRMED,
) -> LegacyUser:
    return LegacyUser(
        id=uuid4(),
        email=email,
        name=name,
        password=password,
        password_hash=_hash(password),
        organization_id=organization_id,
        role=role,
        is_active=is_active,
        confirmed_at=confirmed_at,
    )


def _put_database_at_0002(url: str) -> None:
    upgrade_to_head(url)
    with alembic_config(url) as config:
        command.downgrade(config, "0001")
        command.upgrade(config, "0002")
    assert current_revision(url) == "0002"


def _insert_task_02_data(url: str) -> LegacyData:
    """Raw rows are fine here: at 0002 the schema is the interface."""
    org_one, org_two = uuid4(), uuid4()
    users = [
        _user(
            "admin@romashka.test",
            "Анна Администратор",
            ADMIN_PASSWORD,
            org_one,
            role="administrator",
        ),
        _user(
            "employee@romashka.test", "Борис Сотрудник", EMPLOYEE_PASSWORD, org_one, role="employee"
        ),
        _user(
            "gone@romashka.test",
            "Глеб Отключённый",
            DEACTIVATED_PASSWORD,
            org_one,
            role="employee",
            is_active=False,
        ),
        _user(
            "new@lutik.test",
            "Вера Новая",
            REGISTRANT_PASSWORD,
            org_two,
            role="administrator",
            confirmed_at=None,
        ),
    ]
    engine = create_engine(url)
    try:
        with engine.begin() as conn:
            for org_id, org_name in ((org_one, "Ромашка"), (org_two, "Лютик")):
                conn.execute(
                    text("INSERT INTO organizations (id, name, created_at) VALUES (:i, :n, :c)"),
                    {"i": org_id, "n": org_name, "c": CREATED},
                )
            for u in users:
                conn.execute(
                    text(
                        "INSERT INTO users (id, organization_id, email, name, password_hash, "
                        "role, is_active, confirmed_at, created_at) VALUES (:id, :org, :email, "
                        ":name, :hash, :role, :active, :confirmed, :created)"
                    ),
                    {
                        "id": u.id,
                        "org": u.organization_id,
                        "email": u.email,
                        "name": u.name,
                        "hash": u.password_hash,
                        "role": u.role,
                        "active": u.is_active,
                        "confirmed": u.confirmed_at,
                        "created": CREATED,
                    },
                )
            employee, registrant = users[1], users[3]
            conn.execute(
                text(
                    "INSERT INTO sessions (id, organization_id, user_id, token_hash, created_at, "
                    "expires_at) VALUES (:id, :org, :user, :hash, :c, :e)"
                ),
                {
                    "id": uuid4(),
                    "org": employee.organization_id,
                    "user": employee.id,
                    "hash": "a" * 64,
                    "c": CREATED,
                    "e": EXPIRES,
                },
            )
            conn.execute(
                text(
                    "INSERT INTO user_tokens (id, organization_id, user_id, purpose, token_hash, "
                    "created_at, expires_at) VALUES (:id, :org, :user, 'confirmation', :hash, "
                    ":c, :e)"
                ),
                {
                    "id": uuid4(),
                    "org": registrant.organization_id,
                    "user": registrant.id,
                    "hash": "b" * 64,
                    "c": CREATED,
                    "e": EXPIRES,
                },
            )
    finally:
        engine.dispose()
    return LegacyData(url, users, employee, registrant)


@pytest.fixture
def task_02_data() -> Iterator[LegacyData]:
    """The test database at 0002 with task 0.2 data; at the end it is back at head and empty."""
    url = TestDatabaseSettings().test_database_url  # pyright: ignore[reportCallIssue] -- filled from env
    try:
        _put_database_at_0002(url)
        yield _insert_task_02_data(url)
    finally:
        with alembic_config(url) as config:
            command.downgrade(config, "0001")  # drops the data with the tables
        upgrade_to_head(url)


def _rows(url: str, sql: str) -> list[dict[str, Any]]:
    engine = create_engine(url)
    try:
        with engine.connect() as conn:
            return [dict(row) for row in conn.execute(text(sql)).mappings()]
    finally:
        engine.dispose()


def _columns(url: str, table: str) -> set[str]:
    engine = create_engine(url)
    try:
        return {c["name"] for c in inspect(engine).get_columns(table)}
    finally:
        engine.dispose()


def _tables(url: str) -> set[str]:
    engine = create_engine(url)
    try:
        return set(inspect(engine).get_table_names())
    finally:
        engine.dispose()


def test_upgrade_keeps_every_user_with_email_hash_and_confirmation(
    task_02_data: LegacyData,
) -> None:
    # FR-14 «Migration: Formerly deactivated users become ordinary users and can sign in»
    url = task_02_data.url

    upgrade_to_head(url)

    assert current_revision(url) != "0002"
    rows = {r["id"]: r for r in _rows(url, "SELECT * FROM users")}
    assert set(rows) == {u.id for u in task_02_data.users}
    for u in task_02_data.users:
        assert rows[u.id]["email"] == u.email
        assert rows[u.id]["password_hash"] == u.password_hash
        assert rows[u.id]["confirmed_at"] == u.confirmed_at
        assert rows[u.id]["name"] == u.name


def test_upgrade_leaves_the_schema_without_organizations_roles_and_invitations(
    task_02_data: LegacyData,
) -> None:
    # FR-14 «Migration: Formerly deactivated users become ordinary users and can sign in»
    url = task_02_data.url

    upgrade_to_head(url)

    assert _columns(url, "users") == USER_COLUMNS
    assert "organization_id" not in _columns(url, "sessions")
    assert "organization_id" not in _columns(url, "user_tokens")
    tables = _tables(url)
    assert "organizations" not in tables
    assert "invitations" not in tables


def test_upgrade_keeps_the_session_and_the_open_token_of_their_users(
    task_02_data: LegacyData,
) -> None:
    # FR-14 «Migration: Formerly deactivated users become ordinary users and can sign in»
    url = task_02_data.url

    upgrade_to_head(url)

    assert current_revision(url) != "0002"
    sessions = _rows(url, "SELECT user_id FROM sessions")
    tokens = _rows(url, "SELECT user_id FROM user_tokens")
    assert [s["user_id"] for s in sessions] == [task_02_data.session_user.id]
    assert [t["user_id"] for t in tokens] == [task_02_data.token_user.id]


async def test_formerly_deactivated_user_and_administrator_sign_in_after_the_upgrade(
    task_02_data: LegacyData, mail: FakeMailSender, clock: SettableClock
) -> None:
    # FR-14 «Migration: Formerly deactivated users become ordinary users and can sign in»
    with ThreadPoolExecutor(max_workers=1) as pool:  # Alembic runs its own event loop
        pool.submit(upgrade_to_head, task_02_data.url).result()
    assert current_revision(task_02_data.url) != "0002"
    app = create_app(settings_for(task_02_data.url))
    app.dependency_overrides[get_mail_sender] = lambda: mail
    app.dependency_overrides[get_clock] = lambda: clock
    signed_in: dict[str, tuple[int, Any]] = {}

    async with app.router.lifespan_context(app):
        factories = Factories(app, mail, clock)
        try:
            for u in task_02_data.users[:3]:
                client = await factories.open_client()
                response = await sign_in(client, u.email, u.password)
                signed_in[u.email] = (response.status_code, response.json())
        finally:
            await factories.close()

    for u in task_02_data.users[:3]:
        status, body = signed_in[u.email]
        assert status == HTTPStatus.OK, f"{u.email}: {body}"
        assert body["user_id"] == str(u.id)
        assert body["email"] == u.email
        assert set(body) == {"user_id", "name", "email"}


def test_downgrade_gives_each_user_an_organization_of_their_own(
    task_02_data: LegacyData,
) -> None:
    # FR-14 «Migration» + design «Rollback»
    url = task_02_data.url
    upgrade_to_head(url)
    assert current_revision(url) != "0002"

    with alembic_config(url) as config:
        command.downgrade(config, "0002")

    assert current_revision(url) == "0002"
    users = _rows(url, "SELECT id, name, organization_id, role, is_active FROM users")
    orgs = {o["id"]: o["name"] for o in _rows(url, "SELECT id, name FROM organizations")}
    assert len(users) == len(task_02_data.users)
    assert len({u["organization_id"] for u in users}) == len(users)  # one organization each
    by_id = {u.id: u for u in task_02_data.users}
    for row in users:
        assert orgs[row["organization_id"]] == by_id[row["id"]].name
        assert row["role"] == "administrator"
        assert row["is_active"] is True
    assert _rows(url, "SELECT 1 FROM invitations") == []


def test_downgrade_fills_organization_of_sessions_and_tokens_from_their_user(
    task_02_data: LegacyData,
) -> None:
    # FR-14 «Migration» + design «Rollback»
    url = task_02_data.url
    upgrade_to_head(url)
    assert current_revision(url) != "0002"

    with alembic_config(url) as config:
        command.downgrade(config, "0002")

    user_orgs = {
        r["id"]: r["organization_id"] for r in _rows(url, "SELECT id, organization_id FROM users")
    }
    sessions = _rows(url, "SELECT user_id, organization_id FROM sessions")
    tokens = _rows(url, "SELECT user_id, organization_id FROM user_tokens")
    assert [(s["user_id"], s["organization_id"]) for s in sessions] == [
        (task_02_data.session_user.id, user_orgs[task_02_data.session_user.id])
    ]
    assert [(t["user_id"], t["organization_id"]) for t in tokens] == [
        (task_02_data.token_user.id, user_orgs[task_02_data.token_user.id])
    ]
