"""Helpers of the project and placement suites: the engine seam, the project routes, the mail."""

import json
from collections.abc import Mapping, Sequence
from datetime import datetime, timedelta
from http import HTTPStatus
from pathlib import Path
from typing import Any

from fastapi import FastAPI
from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import PlacementEngine, get_placement_engine
from tests.factories import API, VERA_EMAIL, Factories
from tests.mail_factory import INBOX, SENT, raw_email

ANNA_LOGIN = "anna@yandex.ru"
VERA_LOGIN = "vera@yandex.ru"
PETROV = "Сергей Петров <s.petrov@stroymaster.example>"
PETROV_ADDRESS = "s.petrov@stroymaster.example"
SMIRNOVA = "Ольга Смирнова <o.smirnova@interior-studio.example>"
SMIRNOVA_ADDRESS = "o.smirnova@interior-studio.example"
UNKNOWN_ID = "00000000-0000-4000-8000-000000000000"

DEMO_DIR = Path(__file__).resolve().parents[2] / "docker" / "greenmail" / "demo"
DEMO_LOGINS = ("anna@demo.test", "anna.work@demo.test")
RENOVATION = "Ремонт офиса"
PURCHASE = "Закупка техники"
CONFERENCE = "Конференция ТехФорум"
# The demo project descriptions of the brief «Slice 2».
DEMO_PROJECTS = {
    RENOVATION: "Ремонт офиса на Лесной: смета, график работ, акты, дизайн переговорной",
    PURCHASE: "Закупка техники: ноутбуки, мониторы, серверы, коммерческие предложения, "
    "счета и сроки поставки",
    CONFERENCE: "Участие в конференции ТехФорум: программа, доклад, стенд, бронирование зала",
}


def use_engine(app: FastAPI, engine: PlacementEngine) -> None:
    """From now on the routes of `app` fill projects with `engine`."""
    app.dependency_overrides[get_placement_engine] = lambda: engine


async def signed_in_with_mailbox(
    factories: Factories, login: str = ANNA_LOGIN, *, email: str | None = None
) -> AsyncClient:
    """A new confirmed user signed in with the mailbox `login` connected (Анна by default)."""
    account = (
        await factories.confirmed_user()
        if email is None
        else await factories.confirmed_user(email=email, name="Вера Смирнова")
    )
    client = await factories.signed_in(account)
    await factories.connect_mailbox(client, login)
    return client


async def vera_with_mailbox(factories: Factories) -> AsyncClient:
    """Вера signed in with vera@yandex.ru connected."""
    return await signed_in_with_mailbox(factories, VERA_LOGIN, email=VERA_EMAIL)


def letter(  # noqa: PLR0913 -- one email of a scenario has this many independent parts
    number: int,
    subject: str,
    now: datetime,
    *,
    days_ago: float,
    text: str = "Текст письма",
    sender: str = PETROV,
    to: Sequence[str] = (ANNA_LOGIN,),
    cc: Sequence[str] = (),
    reply_to: int | None = None,
    references: Sequence[int] = (),
) -> bytes:
    """A raw email with the Message-ID `<p{number}@stroymaster.example>`; replies name numbers."""

    def message_id(n: int) -> str:
        return f"<p{n}@stroymaster.example>"

    return raw_email(
        subject=subject,
        sender=sender,
        to=to,
        cc=cc,
        sent_at=now - timedelta(days=days_ago),
        message_id=message_id(number),
        in_reply_to=None if reply_to is None else message_id(reply_to),
        references=[message_id(n) for n in references],
        text=text,
    )


def put(reader: FakeMailReader, raw: bytes, login: str = ANNA_LOGIN) -> None:
    """Put a raw email in the inbox of `login`."""
    reader.add(login, INBOX, raw)


def load_demo_mail(
    reader: FakeMailReader,
    now: datetime,
    *,
    logins: Mapping[str, str] | None = None,
    newest_first: bool = False,
) -> None:
    """Put the demo `.eml` files into the fake as `manifest.json` lists them, arrived 30 days ago.

    `logins` renames the demo mailboxes; `newest_first` puts them in reverse, so they are read in
    another order.
    """
    entries: list[dict[str, Any]] = json.loads((DEMO_DIR / "manifest.json").read_text("utf-8"))
    arrivals = [
        (entry, now - timedelta(days=30) + timedelta(hours=index))
        for index, entry in enumerate(entries)
    ]
    for entry, arrived in reversed(arrivals) if newest_first else arrivals:
        login = str(entry["mailbox"])
        reader.add(
            (logins or {}).get(login, login),
            INBOX if entry["folder"] == "INBOX" else SENT,
            (DEMO_DIR / str(entry["file"])).read_bytes(),
            seen=bool(entry["seen"]),
            internal_date=arrived,
        )


async def list_projects(client: AsyncClient) -> list[dict[str, Any]]:
    """GET /projects."""
    response = await client.get(f"{API}/projects")
    assert response.status_code == HTTPStatus.OK, response.text
    projects: list[dict[str, Any]] = response.json()
    return projects


async def open_project(client: AsyncClient, project_id: str) -> dict[str, Any]:
    """GET /projects/{id}: the `ProjectTree`."""
    response = await client.get(f"{API}/projects/{project_id}")
    assert response.status_code == HTTPStatus.OK, response.text
    tree: dict[str, Any] = response.json()
    return tree


async def fill_project(client: AsyncClient, project_id: str) -> dict[str, Any]:
    """POST /projects/{id}/fill: the rebuilt `ProjectTree`."""
    response = await client.post(f"{API}/projects/{project_id}/fill")
    assert response.status_code == HTTPStatus.OK, response.text
    tree: dict[str, Any] = response.json()
    return tree


def threads_of(tree: Mapping[str, Any]) -> dict[str, dict[str, Any]]:
    """The threads of a tree by id, each once although every counterparty repeats it."""
    threads: dict[str, dict[str, Any]] = {}
    for counterparty in tree["counterparties"]:
        for thread in counterparty["threads"]:
            known = threads.setdefault(thread["id"], {"name": thread["name"], "chains": {}})
            for chain in thread["chains"]:
                known["chains"][chain["id"]] = chain
    return threads


def thread_subjects(tree: Mapping[str, Any]) -> dict[str, set[str]]:
    """Thread name → the subjects of its chains."""
    return {
        thread["name"]: {chain["subject"] for chain in thread["chains"].values()}
        for thread in threads_of(tree).values()
    }


def placed_chains(tree: Mapping[str, Any]) -> list[dict[str, Any]]:
    """The chains in the threads of a tree, each once."""
    return [chain for thread in threads_of(tree).values() for chain in thread["chains"].values()]


def all_subjects(tree: Mapping[str, Any]) -> set[str]:
    """The subjects of every chain of a project: in threads and in «Неразобранное»."""
    return {chain["subject"] for chain in placed_chains(tree)} | {
        chain["subject"] for chain in tree["unassigned"]
    }


def tree_snapshot(tree: Mapping[str, Any]) -> tuple[Any, ...]:
    """Threads with names, chains and placements, and «Неразобранное», without ids."""

    def chain_key(chain: Mapping[str, Any]) -> tuple[str, str, float]:
        placement = chain["placement"]
        return chain["subject"], placement["engine_version"], placement["similarity"]

    threads = sorted(
        (thread["name"], tuple(sorted(chain_key(c) for c in thread["chains"].values())))
        for thread in threads_of(tree).values()
    )
    unassigned = tuple(sorted(chain_key(chain) for chain in tree["unassigned"]))
    return tuple(threads), unassigned
