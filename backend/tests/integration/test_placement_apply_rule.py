"""FR-47 through the HTTP API: which chains a rule lists and moves, and which it leaves alone.

Also the FR-46 scenario «a new rule moves nothing». Edits: `test_placement_apply_rule_edits.py`;
requests: `test_placement_apply_rule_requests.py`.
"""

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine
from tests.factories import (
    Factories,
    chain_id_of,
    chain_location,
    create_rule,
    move_chain,
    project_threads,
    take_out_chain,
)
from tests.hand_placement import ACT, ESTIMATE, MANUAL, MONITORS
from tests.project_trees import (
    fill_project,
    letter,
    open_project,
    put,
    thread_subjects,
    use_engine,
)
from tests.rule_support import (
    ACT_OF_RECONCILIATION,
    ADDRESS,
    DOMAIN,
    EXCLUDED,
    NONE_STATE,
    SUBJECT,
    TECHSNAB,
    VOLKOV,
    VOLKOV_ADDRESS,
    anna_with_two_projects,
    apply_rule,
    by_engine,
    by_rule,
    engine_places,
    project_ref,
    read_again,
    read_volkov_chains,
    rule_moves,
)


async def test_fr47_a_chain_in_no_project_is_listed_and_placed_by_the_rule(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «A chain in no project»
    anna, _, purchase = await anna_with_two_projects(factories)
    await read_volkov_chains(factories, reader, [MONITORS])
    chain_id = await chain_id_of(anna, MONITORS)
    assert (await chain_location(anna, chain_id))["state"] == "none"

    rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])

    [move] = await rule_moves(anna, rule["id"])
    assert (move["chain_id"], move["subject"]) == (chain_id, MONITORS)
    assert move["latest_email_at"]
    assert move["current"] == {"state": "none", "project": None, "thread": None}
    assert move["target"] == {"project": project_ref(purchase), "thread_name": None}

    assert await apply_rule(anna, rule["id"], [chain_id]) == 1

    location = await chain_location(anna, chain_id)
    assert location["state"] == "placed"
    assert location["project"] == project_ref(purchase)
    assert location["thread"] is None
    assert location["placement"] == by_rule(DOMAIN, TECHSNAB)
    tree = await open_project(anna, purchase["id"])
    assert [chain["subject"] for chain in tree["unassigned"]] == [MONITORS]


async def test_fr47_a_chain_of_the_engine_moves_to_the_thread_of_the_rule(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «A chain of the engine»
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    put(reader, letter(1, ESTIMATE, now, days_ago=5, text="Ремонт офиса"))
    put(reader, letter(2, MONITORS, now, days_ago=2, sender=VOLKOV, text="Мониторы для ремонта"))
    await read_again(factories)
    await engine_places(factories, anna, renovation["id"])
    chain_id = await chain_id_of(anna, MONITORS)
    [old_thread] = await project_threads(anna, renovation["id"])
    assert old_thread["name"] == ESTIMATE
    assert (await chain_location(anna, chain_id))["placement"] == by_engine("fake-1", 0.5)
    rule = await create_rule(anna, SUBJECT, "мониторы", purchase["id"], "Мониторы")

    [move] = await rule_moves(anna, rule["id"])
    assert move["chain_id"] == chain_id
    assert move["current"] == {
        "state": "placed",
        "project": project_ref(renovation),
        "thread": old_thread,
    }
    assert move["target"] == {"project": project_ref(purchase), "thread_name": "Мониторы"}

    assert await apply_rule(anna, rule["id"], [chain_id]) == 1

    assert thread_subjects(await open_project(anna, purchase["id"])) == {"Мониторы": {MONITORS}}
    location = await chain_location(anna, chain_id)
    assert location["project"] == project_ref(purchase)
    assert location["placement"] == by_rule(SUBJECT, "мониторы")
    assert thread_subjects(await open_project(anna, renovation["id"])) == {ESTIMATE: {ESTIMATE}}


async def test_fr47_not_now_moves_nothing(factories: Factories, reader: FakeMailReader) -> None:
    # FR-47 «Not now»: the page listed the chain, «Не сейчас» sends nothing
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    put(reader, letter(1, MONITORS, now, days_ago=3, sender=VOLKOV, text="Мониторы для ремонта"))
    await read_again(factories)
    await engine_places(factories, anna, renovation["id"])
    chain_id = await chain_id_of(anna, MONITORS)
    before = await chain_location(anna, chain_id)
    assert before["placement"] == by_engine("fake-1", 0.5)

    rule = await create_rule(anna, SUBJECT, "мониторы", purchase["id"])
    assert [m["chain_id"] for m in await rule_moves(anna, rule["id"])] == [chain_id]

    assert await chain_location(anna, chain_id) == before
    assert (await open_project(anna, purchase["id"]))["unassigned"] == []


async def test_fr46_a_new_rule_moves_nothing_until_it_is_applied(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46 «A new rule moves nothing»
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    put(reader, letter(1, MONITORS, now, days_ago=3, sender=VOLKOV, text="Мониторы для ремонта"))
    await read_again(factories)
    await engine_places(factories, anna, renovation["id"])
    chain_id = await chain_id_of(anna, MONITORS)
    before = await chain_location(anna, chain_id)

    await create_rule(anna, SUBJECT, "мониторы", purchase["id"])

    after = await chain_location(anna, chain_id)
    assert after == before
    assert after["project"] == project_ref(renovation)
    assert after["placement"] == by_engine("fake-1", 0.5)


async def test_fr47_a_chain_placed_by_hand_is_not_listed_and_not_moved(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «A chain placed by hand»
    anna, renovation, purchase = await anna_with_two_projects(factories)
    await read_volkov_chains(factories, reader, [ACT])
    act_id = await chain_id_of(anna, ACT)
    await move_chain(anna, act_id, purchase["id"])

    rule = await create_rule(anna, SUBJECT, "акт работ", renovation["id"])

    assert await rule_moves(anna, rule["id"]) == []
    assert await apply_rule(anna, rule["id"], [act_id]) == 0
    location = await chain_location(anna, act_id)
    assert location["project"] == project_ref(purchase)
    assert location["placement"] == MANUAL


async def test_fr47_a_chain_taken_out_is_not_listed_and_not_moved(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «A chain taken out»
    anna, renovation, purchase = await anna_with_two_projects(factories)
    await read_volkov_chains(factories, reader, [ACT_OF_RECONCILIATION])
    chain_id = await chain_id_of(anna, ACT_OF_RECONCILIATION)
    await move_chain(anna, chain_id, purchase["id"])
    await take_out_chain(anna, chain_id)

    rule = await create_rule(anna, SUBJECT, "акт", renovation["id"])

    assert await rule_moves(anna, rule["id"]) == []
    assert await apply_rule(anna, rule["id"], [chain_id]) == 0
    assert await chain_location(anna, chain_id) == EXCLUDED


async def test_fr47_a_stronger_rule_keeps_its_chain(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «A stronger rule wins»
    anna, renovation, purchase = await anna_with_two_projects(factories)
    await create_rule(anna, ADDRESS, VOLKOV_ADDRESS, renovation["id"])
    await read_volkov_chains(factories, reader, [MONITORS])
    chain_id = await chain_id_of(anna, MONITORS)
    before = await chain_location(anna, chain_id)
    assert before["placement"] == by_rule(ADDRESS, VOLKOV_ADDRESS)

    rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])

    assert await rule_moves(anna, rule["id"]) == []
    assert await apply_rule(anna, rule["id"], [chain_id]) == 0
    assert await chain_location(anna, chain_id) == before
    assert before["project"] == project_ref(renovation)


async def test_fr47_a_chain_of_a_weaker_rule_is_moved_by_a_stronger_new_one(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «A weaker rule's chain»
    anna, renovation, purchase = await anna_with_two_projects(factories)
    await create_rule(anna, DOMAIN, TECHSNAB, renovation["id"])
    await read_volkov_chains(factories, reader, [MONITORS])
    chain_id = await chain_id_of(anna, MONITORS)
    before = await chain_location(anna, chain_id)
    assert before["project"] == project_ref(renovation)
    assert before["thread"] is None
    assert before["placement"] == by_rule(DOMAIN, TECHSNAB)

    rule = await create_rule(anna, ADDRESS, VOLKOV_ADDRESS, purchase["id"])

    [move] = await rule_moves(anna, rule["id"])
    assert move["chain_id"] == chain_id
    assert move["current"] == {
        "state": "placed",
        "project": project_ref(renovation),
        "thread": None,
    }
    assert move["target"] == {"project": project_ref(purchase), "thread_name": None}

    assert await apply_rule(anna, rule["id"], [chain_id]) == 1

    location = await chain_location(anna, chain_id)
    assert location["project"] == project_ref(purchase)
    assert location["thread"] is None
    assert location["placement"] == by_rule(ADDRESS, VOLKOV_ADDRESS)
    purchase_tree = await open_project(anna, purchase["id"])
    assert [chain["subject"] for chain in purchase_tree["unassigned"]] == [MONITORS]
    renovation_tree = await open_project(anna, renovation["id"])
    assert MONITORS not in [chain["subject"] for chain in renovation_tree["unassigned"]]


async def test_fr47_a_chain_already_in_its_project_and_thread_is_not_listed(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «Already in place»
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    put(reader, letter(1, ESTIMATE, now, days_ago=3, text="Ремонт офиса"))
    await read_again(factories)
    await engine_places(factories, anna, renovation["id"])
    chain_id = await chain_id_of(anna, ESTIMATE)
    before = await chain_location(anna, chain_id)
    assert before["thread"]["name"] == ESTIMATE  # type: ignore[index] -- a missing thread fails here
    assert before["placement"] == by_engine("fake-1", 0.5)

    rule = await create_rule(
        anna, ADDRESS, "s.petrov@stroymaster.example", renovation["id"], "смета на ремонт офиса"
    )

    assert await rule_moves(anna, rule["id"]) == []
    assert await chain_location(anna, chain_id) == before


async def test_fr47_a_rule_no_chain_matches_lists_nothing_and_moves_nothing(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «Nothing to move»
    anna, renovation, _ = await anna_with_two_projects(factories)
    await read_volkov_chains(factories, reader, [MONITORS])
    chain_id = await chain_id_of(anna, MONITORS)

    rule = await create_rule(anna, DOMAIN, "nobody.example", renovation["id"])

    assert await rule_moves(anna, rule["id"]) == []
    assert await apply_rule(anna, rule["id"], []) == 0
    assert await chain_location(anna, chain_id) == NONE_STATE


async def test_fr47_a_thread_left_empty_disappears(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «A thread left empty»
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    # the engine names a thread after its earliest chain, so this chain is subject «Мониторы»
    put(reader, letter(1, "Мониторы", now, days_ago=3, sender=VOLKOV, text="Мониторы для ремонта"))
    await read_again(factories)
    await engine_places(factories, anna, renovation["id"])
    chain_id = await chain_id_of(anna, "Мониторы")
    assert [t["name"] for t in await project_threads(anna, renovation["id"])] == ["Мониторы"]
    assert thread_subjects(await open_project(anna, renovation["id"])) == {"Мониторы": {"Мониторы"}}
    rule = await create_rule(anna, SUBJECT, "мониторы", purchase["id"])

    assert await apply_rule(anna, rule["id"], [chain_id]) == 1

    assert "Мониторы" not in [t["name"] for t in await project_threads(anna, renovation["id"])]
    assert "Мониторы" not in thread_subjects(await open_project(anna, renovation["id"]))


async def test_fr47_a_chain_of_the_engine_in_unassigned_moves_into_a_new_thread_of_its_project(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 SHALL: a chain not already in its project and thread is moved
    # (same project, a new thread)
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    put(reader, letter(1, MONITORS, now, days_ago=2, sender=VOLKOV, text="Мониторы для ремонта"))
    await read_again(factories)
    use_engine(factories.app, FakePlacementEngine("fake-1", {"ремонт": 0.2}))
    await fill_project(anna, renovation["id"])
    chain_id = await chain_id_of(anna, MONITORS)
    before = await chain_location(anna, chain_id)
    assert before["project"] == project_ref(renovation)
    assert before["thread"] is None
    assert before["placement"] == by_engine("fake-1", 0.2)
    assert await project_threads(anna, renovation["id"]) == []
    rule = await create_rule(anna, SUBJECT, "мониторы", renovation["id"], "Мониторы")

    [move] = await rule_moves(anna, rule["id"])
    assert move["chain_id"] == chain_id
    assert move["current"] == {
        "state": "placed",
        "project": project_ref(renovation),
        "thread": None,
    }
    assert move["target"] == {"project": project_ref(renovation), "thread_name": "Мониторы"}

    assert await apply_rule(anna, rule["id"], [chain_id]) == 1

    tree = await open_project(anna, renovation["id"])
    assert thread_subjects(tree) == {"Мониторы": {MONITORS}}
    assert tree["unassigned"] == []
    location = await chain_location(anna, chain_id)
    assert location["thread"]["name"] == "Мониторы"
    assert location["placement"] == by_rule(SUBJECT, "мониторы")
