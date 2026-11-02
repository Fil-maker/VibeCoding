"""FR-34 through the HTTP API: a project shown as a tree of counterparties, threads and chains."""

from datetime import datetime, timedelta
from http import HTTPStatus
from typing import Any

from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine
from tests.factories import ANNA_EMAIL, API, Factories, open_chain
from tests.project_trees import (
    ANNA_LOGIN,
    PETROV,
    PETROV_ADDRESS,
    RENOVATION,
    SMIRNOVA,
    SMIRNOVA_ADDRESS,
    UNKNOWN_ID,
    fill_project,
    letter,
    open_project,
    put,
    signed_in_with_mailbox,
    threads_of,
    use_engine,
    vera_with_mailbox,
)

ESTIMATE = "Смета на ремонт офиса"
ACT = "Акт скрытых работ"
DESCRIPTION = "Ремонт офиса на Лесной"
# Every chain of these scenarios mentions «Лесной», so it is sure for the project and its thread.
ENGINE = FakePlacementEngine("fake-1", {"лесной": 0.5})


def estimate_and_act(reader: FakeMailReader, now: datetime) -> None:
    """«Смета на ремонт офиса» (3 emails, Петров first as «С. Петров») and «Акт скрытых работ»."""
    put(
        reader,
        letter(
            1,
            ESTIMATE,
            now,
            days_ago=10,
            text="Смета, объект на Лесной",
            sender=f"С. Петров <{PETROV_ADDRESS}>",
        ),
    )
    put(
        reader,
        letter(
            2,
            "Re: " + ESTIMATE,
            now,
            days_ago=9,
            text="Спасибо, Лесной",
            sender=ANNA_LOGIN,
            to=[PETROV_ADDRESS],
            reply_to=1,
        ),
    )
    put(
        reader,
        letter(
            3,
            "Re: " + ESTIMATE,
            now,
            days_ago=8,
            text="Уточнил по Лесной",
            reply_to=2,
            references=[1, 2],
        ),
    )
    put(reader, letter(10, ACT, now, days_ago=5, text="Акт по объекту на Лесной"))


async def filled_renovation(factories: Factories, anna: AsyncClient) -> dict[str, Any]:
    """Create «Ремонт офиса», fill it with the fake engine and return its tree."""
    await factories.read_due()
    use_engine(factories.app, ENGINE)
    project = await factories.create_project(anna, RENOVATION, DESCRIPTION)
    await fill_project(anna, project["id"])
    return await open_project(anna, project["id"])


async def test_fr34_the_tree_shows_the_counterparty_its_thread_and_chains(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-34 «The tree of a project»
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    estimate_and_act(reader, now)

    tree = await filled_renovation(factories, anna)

    assert (tree["name"], tree["description"]) == (RENOVATION, DESCRIPTION)
    [counterparty] = tree["counterparties"]
    assert (counterparty["address"], counterparty["name"]) == (PETROV_ADDRESS, "Сергей Петров")
    [thread] = counterparty["threads"]
    assert thread["name"] == ESTIMATE
    chains = {chain["subject"]: chain for chain in thread["chains"]}
    assert set(chains) == {ESTIMATE, ACT}
    assert (chains[ESTIMATE]["email_count"], chains[ACT]["email_count"]) == (3, 1)
    assert datetime.fromisoformat(chains[ESTIMATE]["latest_email_at"]) == now - timedelta(days=8)
    assert datetime.fromisoformat(chains[ACT]["latest_email_at"]) == now - timedelta(days=5)
    assert tree["unassigned"] == []


async def test_fr34_a_chain_with_two_counterparties_is_under_both_in_the_same_thread(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-34 «A chain with two counterparties»
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    put(
        reader,
        letter(20, "Дизайн переговорной", now, days_ago=4, text="Эскизы для Лесной", cc=[SMIRNOVA]),
    )
    put(
        reader,
        letter(
            21,
            "Re: Дизайн переговорной",
            now,
            days_ago=3,
            text="Лесной: вариант 2",
            sender=SMIRNOVA,
            cc=[PETROV],
            reply_to=20,
        ),
    )

    tree = await filled_renovation(factories, anna)

    counterparties = tree["counterparties"]
    assert {(c["name"], c["address"]) for c in counterparties} == {
        ("Ольга Смирнова", SMIRNOVA_ADDRESS),
        ("Сергей Петров", PETROV_ADDRESS),
    }
    placements = [
        (thread["id"], [chain["subject"] for chain in thread["chains"]])
        for counterparty in counterparties
        for thread in counterparty["threads"]
    ]
    assert placements[0] == placements[1]
    assert placements[0][1] == ["Дизайн переговорной"]
    assert len(threads_of(tree)) == 1


async def test_fr34_a_counterparty_that_wrote_without_a_name_is_named_by_its_address(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-34: named by the latest name it wrote with, else by the address
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    put(
        reader,
        letter(
            30,
            "Доступ в здание",
            now,
            days_ago=2,
            text="Пропуск на Лесной",
            sender="foreman@stroy.test",
        ),
    )

    tree = await filled_renovation(factories, anna)

    assert [(c["address"], c["name"]) for c in tree["counterparties"]] == [
        ("foreman@stroy.test", "foreman@stroy.test")
    ]


async def test_fr34_a_chain_between_own_addresses_is_under_without_counterparty(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-34 «A chain without counterparties»
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    put(
        reader,
        letter(
            40,
            "Заметка себе",
            now,
            days_ago=1,
            text="Позвонить про Лесной",
            sender=ANNA_LOGIN,
            to=[ANNA_EMAIL],
        ),
    )

    tree = await filled_renovation(factories, anna)

    [counterparty] = tree["counterparties"]
    assert (counterparty["address"], counterparty["name"]) == (None, "Без контрагента")
    [thread] = counterparty["threads"]
    assert [chain["subject"] for chain in thread["chains"]] == ["Заметка себе"]


async def test_fr34_a_chain_of_the_tree_opens_with_its_emails(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-34 «Opening a chain from the tree»
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    estimate_and_act(reader, now)
    tree = await filled_renovation(factories, anna)
    [thread] = threads_of(tree).values()
    [act_id] = [cid for cid, chain in thread["chains"].items() if chain["subject"] == ACT]

    chain = await open_chain(anna, act_id)

    assert chain["subject"] == ACT
    [email] = chain["emails"]
    assert email["subject"] == ACT
    assert email["text"].strip() == "Акт по объекту на Лесной"


async def test_fr34_another_users_project_is_not_found(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-34 «Another user's project»
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    estimate_and_act(reader, now)
    await factories.read_due()
    project = await factories.create_project(anna, RENOVATION, DESCRIPTION)
    vera = await vera_with_mailbox(factories)

    responses = [
        await vera.get(f"{API}/projects/{project['id']}"),
        await vera.get(f"{API}/projects/{UNKNOWN_ID}"),
    ]

    assert [r.status_code for r in responses] == [HTTPStatus.NOT_FOUND] * 2
    assert {r.json()["error"]["code"] for r in responses} == {"not_found"}
    assert RENOVATION not in responses[0].text
