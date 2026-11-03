"""Helpers of the placement-rule suites (FR-35 to FR-37, FR-39, FR-42, FR-43 to FR-46)."""

from datetime import timedelta
from typing import Any

from httpx import AsyncClient

from app.platform.placement_engine import FakePlacementEngine, PlacementEngine
from tests.factories import Factories
from tests.project_trees import PURCHASE, RENOVATION, signed_in_with_mailbox

ADDRESS = "address"
DOMAIN = "domain"
SUBJECT = "subject"
VOLKOV = "Игорь Волков <i.volkov@techsnab.example>"
VOLKOV_ADDRESS = "i.volkov@techsnab.example"
NO_ENGINE_MATCH = FakePlacementEngine("fake-1", {})


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
