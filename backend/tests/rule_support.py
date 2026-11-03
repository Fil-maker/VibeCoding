"""Helpers of the placement-rule suites (FR-35 to FR-37, FR-39, FR-42, FR-43 to FR-46)."""

from datetime import timedelta
from http import HTTPStatus
from typing import Any

from httpx import AsyncClient, Response

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine, PlacementEngine
from tests.factories import API, VERA_EMAIL, Factories
from tests.project_trees import (
    PURCHASE,
    RENOVATION,
    fill_project,
    letter,
    put,
    signed_in_with_mailbox,
    use_engine,
)

ADDRESS = "address"
DOMAIN = "domain"
SUBJECT = "subject"
VOLKOV = "Игорь Волков <i.volkov@techsnab.example>"
VOLKOV_ADDRESS = "i.volkov@techsnab.example"
NO_ENGINE_MATCH = FakePlacementEngine("fake-1", {})
CONTRACT = "Договор поставки"
ACT_OF_RECONCILIATION = "Акт сверки"
TECHSNAB = "techsnab.example"
NONE_STATE = {"state": "none", "project": None, "thread": None, "placement": None}
EXCLUDED = {"state": "excluded", "project": None, "thread": None, "placement": None}


def by_rule(condition: str, value: str) -> dict[str, Any]:
    """The `Placement` of a chain placed by a rule."""
    return {
        "kind": "rule",
        "engine_version": None,
        "similarity": None,
        "rule": {"condition": condition, "value": value},
    }


def by_engine(version: str, similarity: float) -> dict[str, Any]:
    """The `Placement` of a chain placed by the engine."""
    return {"kind": "engine", "engine_version": version, "similarity": similarity, "rule": None}


async def read_again(factories: Factories, engine: PlacementEngine = NO_ENGINE_MATCH) -> None:
    """Five minutes later, a reading pass that places the new chains with `engine`."""
    factories.clock.advance(timedelta(minutes=5))
    await factories.read_due(engine)


async def anna_with_two_projects(
    factories: Factories,
) -> tuple[AsyncClient, dict[str, Any], dict[str, Any]]:
    """Анна with a mailbox and the unfilled projects «Ремонт офиса» and «Закупка техники»."""
    anna = await signed_in_with_mailbox(factories)
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    purchase = await factories.create_project(anna, PURCHASE, "Закупка техники")
    return anna, renovation, purchase


def project_ref(project: dict[str, Any]) -> dict[str, Any]:
    """The `ProjectRef` of a project summary."""
    return {"id": project["id"], "name": project["name"]}


async def rule_moves_response(client: AsyncClient, rule_id: str) -> Response:
    """GET /placements/by-rule/{rule_id}: the raw answer."""
    return await client.get(f"{API}/placements/by-rule/{rule_id}")


async def rule_moves(client: AsyncClient, rule_id: str) -> list[dict[str, Any]]:
    """GET /placements/by-rule/{rule_id}: the `moves` of `RuleMoves`."""
    response = await rule_moves_response(client, rule_id)
    assert response.status_code == HTTPStatus.OK, response.text
    moves: list[dict[str, Any]] = response.json()["moves"]
    return moves


async def apply_rule_response(client: AsyncClient, rule_id: str, chain_ids: list[str]) -> Response:
    """POST /placements/by-rule/{rule_id}: the raw answer."""
    return await client.post(f"{API}/placements/by-rule/{rule_id}", json={"chain_ids": chain_ids})


async def apply_rule(client: AsyncClient, rule_id: str, chain_ids: list[str]) -> int:
    """Apply a rule to the listed chains; returns `moved` of `RuleApplied`."""
    response = await apply_rule_response(client, rule_id, chain_ids)
    assert response.status_code == HTTPStatus.OK, response.text
    return int(response.json()["moved"])


async def read_volkov_chains(
    factories: Factories, reader: FakeMailReader, subjects: list[str]
) -> None:
    """Chains from Игорь Волков, one per subject, the first the oldest; read into no project."""
    now = factories.clock.now()
    for number, subject in enumerate(subjects, start=1):
        put(reader, letter(number, subject, now, days_ago=10 - number, sender=VOLKOV))
    await read_again(factories)


async def engine_places(
    factories: Factories, client: AsyncClient, project_id: str, keyword: str = "ремонт"
) -> None:
    """Fill the project with an engine that takes every chain whose text holds `keyword`."""
    use_engine(factories.app, FakePlacementEngine("fake-1", {keyword: 0.5}))
    await fill_project(client, project_id)


async def vera_with_project(factories: Factories) -> tuple[AsyncClient, dict[str, Any]]:
    """Вера signed in, with her own project «Отпуск»."""
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))
    return vera, await factories.create_project(vera, "Отпуск", "Отпуск в августе")
