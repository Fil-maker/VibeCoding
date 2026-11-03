"""FR-42 and the by-hand scenarios of FR-36, FR-37: placements by hand are kept by the engine."""

from datetime import timedelta
from typing import Any

from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine, PlacementEngine
from tests.factories import (
    Factories,
    chain_id_of,
    chain_location,
    list_chains,
    move_chain,
    project_threads,
    take_out_chain,
)
from tests.hand_placement import (
    ACT,
    ACTS_THREAD,
    DESIGN,
    ESTIMATE,
    MANUAL,
    MONITORS,
    anna_with_chains,
    chain_in_tree,
)
from tests.project_trees import (
    PURCHASE,
    RENOVATION,
    fill_project,
    letter,
    open_project,
    put,
    thread_subjects,
    use_engine,
)

ACCEPTANCE = "Акт приёмки работ"
EXCLUDED = {"state": "excluded", "project": None, "thread": None, "placement": None}


async def read_again(factories: Factories, engine: PlacementEngine) -> None:
    """Five minutes later, a reading pass that places new chains with `engine`."""
    factories.clock.advance(timedelta(minutes=5))
    await factories.read_due(engine)


async def joined_chain(client: AsyncClient) -> dict[str, Any]:
    """The one chain of the user that holds three emails."""
    [chain] = [c for c in await list_chains(client) if c["email_count"] == 3]
    return chain


# --- FR-42 Placements by hand are kept ---


async def test_fr42_a_new_email_in_a_chain_placed_by_hand_leaves_it_there(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-42 «A new email in a chain placed by hand»
    now = factories.clock.now()
    anna = await anna_with_chains(factories, reader, [ACT])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    purchase = await factories.create_project(anna, PURCHASE, "Закупка: акт")
    use_engine(factories.app, FakePlacementEngine("fake-1", {"акт": 0.9}))
    await fill_project(anna, purchase["id"])
    act_id = await chain_id_of(anna, ACT)
    before = await move_chain(anna, act_id, renovation["id"], new_thread_name=ACTS_THREAD)
    put(reader, letter(5, "Re: " + ACT, now, days_ago=0.1, text="Акт подписан", reply_to=1))

    await read_again(factories, FakePlacementEngine("fake-2", {"акт": 0.9}))

    assert await chain_location(anna, act_id) == before
    assert before["thread"]["name"] == ACTS_THREAD
    assert before["placement"] == MANUAL
    [chain] = [c for c in await list_chains(anna) if c["id"] == act_id]
    assert chain["email_count"] == 2


async def test_fr42_a_chain_joined_with_a_chain_of_the_engine_keeps_the_hand_placement(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-42 «Joined with a chain of the engine»: the engine's placement is earlier
    now = factories.clock.now()
    anna = await anna_with_chains(factories, reader, [ESTIMATE, MONITORS])
    engine = FakePlacementEngine("fake-1", {"смет": 0.5})
    use_engine(factories.app, engine)
    renovation = await factories.create_project(anna, RENOVATION, "Смета на ремонт")
    purchase = await factories.create_project(anna, PURCHASE, "Закупка техники")
    await fill_project(anna, renovation["id"])
    estimate = await chain_location(anna, await chain_id_of(anna, ESTIMATE))
    assert estimate["project"] == {"id": renovation["id"], "name": RENOVATION}
    assert estimate["placement"]["kind"] == "engine"
    factories.clock.advance(timedelta(days=1))
    await move_chain(anna, await chain_id_of(anna, MONITORS), purchase["id"])
    put(reader, letter(20, "Re: " + ESTIMATE, now, days_ago=0.1, reply_to=1, references=[1, 2]))

    await read_again(factories, engine)

    joined = await joined_chain(anna)
    location = await chain_location(anna, joined["id"])
    assert location["project"] == {"id": purchase["id"], "name": PURCHASE}
    assert location["placement"] == MANUAL
    assert chain_in_tree(await open_project(anna, renovation["id"]), ESTIMATE) is None


async def test_fr42_a_hand_placement_wins_over_the_engines_whatever_the_dates(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-42: the hand placement is the earlier one here, the engine's the later
    now = factories.clock.now()
    anna = await anna_with_chains(factories, reader, [ESTIMATE, MONITORS])
    engine = FakePlacementEngine("fake-1", {"смет": 0.5})
    use_engine(factories.app, engine)
    renovation = await factories.create_project(anna, RENOVATION, "Смета на ремонт")
    purchase = await factories.create_project(anna, PURCHASE, "Закупка техники")
    await move_chain(anna, await chain_id_of(anna, MONITORS), purchase["id"])
    factories.clock.advance(timedelta(days=1))
    await fill_project(anna, renovation["id"])
    estimate = await chain_location(anna, await chain_id_of(anna, ESTIMATE))
    assert estimate["project"] == {"id": renovation["id"], "name": RENOVATION}
    assert estimate["placement"]["kind"] == "engine"
    put(reader, letter(20, "Re: " + ESTIMATE, now, days_ago=0.1, reply_to=1, references=[1, 2]))

    await read_again(factories, engine)

    location = await chain_location(anna, (await joined_chain(anna))["id"])
    assert location["project"] == {"id": purchase["id"], "name": PURCHASE}
    assert location["placement"] == MANUAL


async def test_fr42_two_chains_placed_by_hand_keep_the_earlier_placement_when_joined(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-42: among placements of one kind it keeps the earliest
    now = factories.clock.now()
    anna = await anna_with_chains(factories, reader, [ESTIMATE, MONITORS])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    purchase = await factories.create_project(anna, PURCHASE, "Закупка техники")
    await move_chain(anna, await chain_id_of(anna, MONITORS), purchase["id"])
    factories.clock.advance(timedelta(days=1))
    await move_chain(anna, await chain_id_of(anna, ESTIMATE), renovation["id"])
    put(reader, letter(20, "Re: " + ESTIMATE, now, days_ago=0.1, reply_to=1, references=[1, 2]))

    await read_again(factories, FakePlacementEngine("fake-1", {}))

    location = await chain_location(anna, (await joined_chain(anna))["id"])
    assert location["project"] == {"id": purchase["id"], "name": PURCHASE}
    assert location["placement"] == MANUAL


async def test_fr42_a_chain_joined_with_a_chain_taken_out_is_in_no_project(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-42 «Joined with a chain taken out»
    now = factories.clock.now()
    anna = await anna_with_chains(factories, reader, [ESTIMATE, MONITORS])
    engine = FakePlacementEngine("fake-1", {"смет": 0.5})
    use_engine(factories.app, engine)
    renovation = await factories.create_project(anna, RENOVATION, "Смета на ремонт")
    await fill_project(anna, renovation["id"])
    estimate = await chain_location(anna, await chain_id_of(anna, ESTIMATE))
    assert estimate["project"] == {"id": renovation["id"], "name": RENOVATION}
    assert estimate["placement"]["kind"] == "engine"
    purchase = await factories.create_project(anna, PURCHASE, "Мониторы")
    await move_chain(anna, await chain_id_of(anna, MONITORS), purchase["id"])
    await take_out_chain(anna, await chain_id_of(anna, MONITORS))
    put(reader, letter(20, "Re: " + ESTIMATE, now, days_ago=0.1, reply_to=1, references=[1, 2]))

    await read_again(factories, engine)

    joined = await joined_chain(anna)
    assert await chain_location(anna, joined["id"]) == EXCLUDED
    assert chain_in_tree(await open_project(anna, renovation["id"]), ESTIMATE) is None


# --- FR-36 Fill a filled project again ---


async def test_fr36_a_chain_placed_by_hand_survives_filling_again(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-36 «Placements by hand survive filling again»
    anna = await anna_with_chains(factories, reader, [ACT, ESTIMATE])
    use_engine(factories.app, FakePlacementEngine("fake-1", {"смет": 0.5, "акт": 0.5}))
    renovation = await factories.create_project(anna, RENOVATION, "Смета и акт")
    await fill_project(anna, renovation["id"])
    act_id = await chain_id_of(anna, ACT)
    thread = (await move_chain(anna, act_id, renovation["id"], new_thread_name=ACTS_THREAD))[
        "thread"
    ]

    tree = await fill_project(anna, renovation["id"])

    location = await chain_location(anna, act_id)
    assert location["thread"] == thread
    assert location["placement"] == MANUAL
    assert thread_subjects(tree)[ACTS_THREAD] == {ACT}
    assert chain_in_tree(tree, ACT)["placement"] == MANUAL  # type: ignore[index]
    assert thread in await project_threads(anna, renovation["id"])


async def test_fr41_a_chain_taken_out_stays_out_after_filling_again(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-41 «The engine does not take it back»: by «Заполнить» on a filled project
    anna = await anna_with_chains(factories, reader, [ACT, ESTIMATE])
    use_engine(factories.app, FakePlacementEngine("fake-1", {"смет": 0.5, "акт": 0.5}))
    renovation = await factories.create_project(anna, RENOVATION, "Смета и акт")
    await fill_project(anna, renovation["id"])
    act_id = await chain_id_of(anna, ACT)
    await take_out_chain(anna, act_id)

    tree = await fill_project(anna, renovation["id"])

    assert await chain_location(anna, act_id) == EXCLUDED
    assert chain_in_tree(tree, ACT) is None
    assert chain_in_tree(tree, ESTIMATE) is not None


async def test_fr36_the_engine_adds_a_sure_chain_to_a_kept_thread(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-36 «The engine adds to a kept thread»
    anna = await anna_with_chains(factories, reader, [ACT, ACCEPTANCE])
    use_engine(factories.app, FakePlacementEngine("fake-1", {"акт": 0.5}))
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт: акт")
    await fill_project(anna, renovation["id"])
    act_id = await chain_id_of(anna, ACT)
    acceptance_id = await chain_id_of(anna, ACCEPTANCE)
    thread = (await move_chain(anna, act_id, renovation["id"], new_thread_name=ACTS_THREAD))[
        "thread"
    ]

    await fill_project(anna, renovation["id"])

    location = await chain_location(anna, acceptance_id)
    assert location["thread"] == thread
    assert location["placement"] == {
        "kind": "engine",
        "engine_version": "fake-1",
        "similarity": 0.5,
        "rule": None,
    }
    assert (await chain_location(anna, act_id))["placement"] == MANUAL


# --- FR-37 Explain every placement ---


async def test_fr37_a_chain_placed_by_hand_shows_no_engine_and_no_similarity_in_the_tree(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-37 «A chain placed by hand»
    anna = await anna_with_chains(factories, reader, [ACT, DESIGN])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    await move_chain(
        anna, await chain_id_of(anna, ACT), renovation["id"], new_thread_name=ACTS_THREAD
    )
    await move_chain(anna, await chain_id_of(anna, DESIGN), renovation["id"])

    tree = await open_project(anna, renovation["id"])

    assert chain_in_tree(tree, ACT)["placement"] == MANUAL  # type: ignore[index]
    assert tree["unassigned"][0]["placement"] == MANUAL
