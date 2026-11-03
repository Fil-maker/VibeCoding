"""Helpers of the placement-by-hand suites (FR-40 to FR-42): read chains, tree lookups."""

from typing import Any

from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from tests.factories import Factories
from tests.project_trees import letter, placed_chains, put, signed_in_with_mailbox

ESTIMATE = "Смета на ремонт офиса"
ACT = "Акт скрытых работ"
DESIGN = "Выбор дизайна переговорной"
MONITORS = "Счёт на мониторы"
DISCOUNT = "Скидка на абонемент в фитнес-клуб"
ACTS_THREAD = "Акты"
MONITORS_THREAD = "Закупка мониторов"
MANUAL = {"kind": "manual", "engine_version": None, "similarity": None, "rule": None}


async def anna_with_chains(
    factories: Factories, reader: FakeMailReader, subjects: list[str]
) -> AsyncClient:
    """Анна with one single-email chain per subject (message numbers 1, 2, ...), read."""
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    for number, subject in enumerate(subjects, start=1):
        put(reader, letter(number, subject, now, days_ago=20 - number, text="Текст"))
    await factories.read_due()
    return anna


def chain_in_tree(tree: dict[str, Any], subject: str) -> dict[str, Any] | None:
    """The chain with this subject in a project tree (a thread or «Неразобранное»), else None."""

    for chain in [*placed_chains(tree), *tree["unassigned"]]:
        if chain["subject"] == subject:
            return chain
    return None
