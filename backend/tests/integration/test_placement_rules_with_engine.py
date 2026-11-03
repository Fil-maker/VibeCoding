"""Rules next to the engine: FR-35, FR-36, FR-37, FR-39 and FR-42 scenarios of placing by rules."""

from datetime import timedelta
from typing import Any

from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine
from tests.factories import (
    Factories,
    chain_id_of,
    chain_location,
    create_rule,
    delete_rule,
    list_chains,
    move_chain,
    project_threads,
    update_rule,
)
from tests.hand_placement import ACT, ACTS_THREAD, DESIGN, ESTIMATE, MANUAL, MONITORS, chain_in_tree
from tests.project_trees import (
    PETROV,
    PETROV_ADDRESS,
    PURCHASE,
    RENOVATION,
    SMIRNOVA,
    SMIRNOVA_ADDRESS,
    all_subjects,
    fill_project,
    letter,
    open_project,
    placed_chains,
    put,
    signed_in_with_mailbox,
    thread_subjects,
    use_engine,
)
from tests.rule_support import (
    ADDRESS,
    DOMAIN,
    NO_ENGINE_MATCH,
    SUBJECT,
    VOLKOV,
    anna_with_two_projects,
    by_engine,
    by_rule,
    read_again,
)

PAINTING = "Смета на покраску стен в офисе"
OTHER_SENDER = "Олег <oleg@stroy.test>"


# --- FR-35 Fill a project by the engine ---


async def test_fr35_a_rule_of_the_filled_project_places_its_chain_first(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-35 «A rule of this project goes first»
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    put(reader, letter(1, DESIGN, now, days_ago=3, sender=SMIRNOVA, text="Дизайн после ремонта"))
    await read_again(factories)
    await create_rule(anna, ADDRESS, SMIRNOVA_ADDRESS, renovation["id"], "Дизайн")
    # without the rule the engine would place the chain, sure, in this project
    use_engine(factories.app, FakePlacementEngine("fake-1", {"ремонт": 0.9}))

    tree = await fill_project(anna, renovation["id"])

    assert thread_subjects(tree) == {"Дизайн": {DESIGN}}
    assert chain_in_tree(tree, DESIGN)["placement"] == by_rule(ADDRESS, SMIRNOVA_ADDRESS)  # type: ignore[index] -- chain_in_tree is Optional; a missing chain fails the test here


async def test_fr35_a_rule_of_another_project_keeps_the_chain_out_of_the_filled_one(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-35 «A rule of another project keeps a chain out»
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    put(reader, letter(1, ACT, now, days_ago=3, text="Акты ремонта"))
    await read_again(factories)
    await create_rule(anna, SUBJECT, "акт работ", purchase["id"])
    # without the rule the engine would place the chain, sure, in «Ремонт офиса»
    use_engine(factories.app, FakePlacementEngine("fake-1", {"ремонт": 0.9}))

    tree = await fill_project(anna, renovation["id"])

    assert ACT not in all_subjects(tree)


# --- FR-36 Fill a filled project again ---


async def test_fr36_an_edited_rule_takes_effect_on_filling_again(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-36 «An edited rule takes effect on filling again»
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    rule = await create_rule(anna, SUBJECT, "акт работ", renovation["id"], ACTS_THREAD)
    put(reader, letter(1, ACT, now, days_ago=3))
    await read_again(factories)
    use_engine(factories.app, NO_ENGINE_MATCH)
    tree = await fill_project(anna, renovation["id"])
    assert thread_subjects(tree) == {ACTS_THREAD: {ACT}}
    await update_rule(anna, rule["id"], SUBJECT, "акт работ", renovation["id"], "Документы")

    tree = await fill_project(anna, renovation["id"])

    assert thread_subjects(tree) == {"Документы": {ACT}}
    assert chain_in_tree(tree, ACT)["placement"] == by_rule(SUBJECT, "акт работ")  # type: ignore[index] -- chain_in_tree is Optional; a missing chain fails the test here
    assert ACTS_THREAD not in [t["name"] for t in await project_threads(anna, renovation["id"])]


async def test_fr36_a_deleted_rule_leaves_its_chain_to_the_engine_on_filling_again(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-36 «A deleted rule on filling again»
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    rule = await create_rule(anna, SUBJECT, "акт работ", renovation["id"], ACTS_THREAD)
    put(reader, letter(1, ACT, now, days_ago=3, text="Акты ремонта"))
    await read_again(factories)
    use_engine(factories.app, FakePlacementEngine("fake-1", {"ремонт": 0.5}))
    await fill_project(anna, renovation["id"])
    assert (await chain_location(anna, await chain_id_of(anna, ACT)))["placement"]["kind"] == "rule"
    await delete_rule(anna, rule["id"])

    tree = await fill_project(anna, renovation["id"])

    chain = chain_in_tree(tree, ACT)
    assert chain is not None
    assert chain["placement"] == by_engine("fake-1", 0.5)


# --- FR-37 Explain every placement ---


async def test_fr37_chains_placed_by_rules_show_the_rule_in_the_tree_and_on_their_page(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-37 «A chain placed by a rule»
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    await create_rule(anna, ADDRESS, PETROV_ADDRESS, renovation["id"])
    await create_rule(anna, DOMAIN, "techsnab.example", purchase["id"])
    await create_rule(anna, SUBJECT, "акт работ", renovation["id"], ACTS_THREAD)
    put(reader, letter(1, ESTIMATE, now, days_ago=3, sender=PETROV))
    put(reader, letter(2, MONITORS, now, days_ago=2, sender=VOLKOV))
    put(reader, letter(3, ACT, now, days_ago=1, sender=OTHER_SENDER))

    await read_again(factories)

    expected = {
        ESTIMATE: by_rule(ADDRESS, PETROV_ADDRESS),
        MONITORS: by_rule(DOMAIN, "techsnab.example"),
        ACT: by_rule(SUBJECT, "акт работ"),
    }
    trees = [await open_project(anna, p["id"]) for p in (renovation, purchase)]
    for subject, placement in expected.items():
        in_trees = [chain_in_tree(tree, subject) for tree in trees]
        [chain] = [c for c in in_trees if c is not None]
        assert chain["placement"] == placement
        location = await chain_location(anna, await chain_id_of(anna, subject))
        assert location["placement"] == placement


async def test_fr37_a_chain_keeps_its_explanation_after_its_rule_is_changed_or_deleted(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-37 «The rule changed after placing»
    now = factories.clock.now()
    anna, _, purchase = await anna_with_two_projects(factories)
    rule = await create_rule(anna, DOMAIN, "techsnab.example", purchase["id"])
    put(reader, letter(1, MONITORS, now, days_ago=1, sender=VOLKOV))
    await read_again(factories)
    chain_id = await chain_id_of(anna, MONITORS)
    expected = by_rule(DOMAIN, "techsnab.example")

    await update_rule(anna, rule["id"], DOMAIN, "techsnab.ru", purchase["id"])

    [in_tree] = (await open_project(anna, purchase["id"]))["unassigned"]
    assert in_tree["placement"] == expected
    assert (await chain_location(anna, chain_id))["placement"] == expected

    await delete_rule(anna, rule["id"])

    [in_tree] = (await open_project(anna, purchase["id"]))["unassigned"]
    assert in_tree["placement"] == expected
    assert (await chain_location(anna, chain_id))["placement"] == expected


# --- FR-39 Place new chains ---


async def test_fr39_a_rule_goes_before_a_sure_engine_match(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-39 «A rule goes before the engine»
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    put(reader, letter(1, ESTIMATE, now, days_ago=5, sender=OTHER_SENDER, text="Смета на ремонт"))
    await read_again(factories)
    engine = FakePlacementEngine("fake-1", {"ремонт": 0.9})
    use_engine(factories.app, engine)
    await fill_project(anna, renovation["id"])
    await create_rule(anna, ADDRESS, PETROV_ADDRESS, purchase["id"])
    put(reader, letter(2, PAINTING, now, days_ago=0.1, sender=PETROV, text="Для ремонта"))

    await read_again(factories, engine)

    assert PAINTING not in all_subjects(await open_project(anna, renovation["id"]))
    [chain] = (await open_project(anna, purchase["id"]))["unassigned"]
    assert (chain["subject"], chain["placement"]) == (PAINTING, by_rule(ADDRESS, PETROV_ADDRESS))


async def test_fr39_a_rule_places_a_new_chain_into_an_unfilled_project(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-39 «A rule into an unfilled project»
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    holiday = await factories.create_project(anna, "Отпуск", "Отпуск в августе")
    await create_rule(anna, SUBJECT, "отпуск", holiday["id"])
    put(reader, letter(1, "Отпуск в июле", now, days_ago=0.1))

    await read_again(factories)

    tree = await open_project(anna, holiday["id"])
    [chain] = tree["unassigned"]
    assert (chain["subject"], chain["placement"]) == ("Отпуск в июле", by_rule(SUBJECT, "отпуск"))
    assert placed_chains(tree) == []


async def test_fr39_a_reply_in_a_chain_placed_by_a_rule_leaves_it_there(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-39: an email that joins a placed chain leaves the chain where it is
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    sure_elsewhere = await factories.create_project(anna, "Сметы", "Сметы и расчёты")
    await create_rule(anna, ADDRESS, PETROV_ADDRESS, renovation["id"], "Смета")
    put(reader, letter(1, ESTIMATE, now, days_ago=3))
    await read_again(factories)
    use_engine(factories.app, NO_ENGINE_MATCH)
    await fill_project(anna, sure_elsewhere["id"])
    chain_id = await chain_id_of(anna, ESTIMATE)
    before = await chain_location(anna, chain_id)
    assert before["placement"] == by_rule(ADDRESS, PETROV_ADDRESS)
    put(reader, letter(2, "Re: " + ESTIMATE, now, days_ago=0.1, reply_to=1))

    # re-judged, the chain would be sure for «Сметы»
    await read_again(factories, FakePlacementEngine("fake-2", {"смет": 0.9}))

    assert await chain_location(anna, chain_id) == before
    [chain] = [c for c in await list_chains(anna) if c["id"] == chain_id]
    assert chain["email_count"] == 2


# --- FR-42 Placements by hand are kept ---


async def test_fr42_a_placement_by_a_rule_wins_over_the_engines_whatever_the_dates(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-42 «A rule's placement over the engine's»: the engine placed first, the rule later
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    put(reader, letter(1, ESTIMATE, now, days_ago=5, text="Смета на ремонт"))
    put(reader, letter(10, MONITORS, now, days_ago=4, sender="sales@tech.example"))
    await read_again(factories)
    engine = FakePlacementEngine("fake-1", {"ремонт": 0.5})
    use_engine(factories.app, engine)
    await fill_project(anna, renovation["id"])
    assert (await chain_location(anna, await chain_id_of(anna, ESTIMATE)))["placement"][
        "kind"
    ] == "engine"
    factories.clock.advance(timedelta(days=1))
    await create_rule(anna, SUBJECT, "мониторы", purchase["id"])
    await fill_project(anna, purchase["id"])
    monitors = await chain_location(anna, await chain_id_of(anna, MONITORS))
    assert monitors["placement"] == by_rule(SUBJECT, "мониторы")
    put(reader, letter(20, "Re: " + ESTIMATE, now, days_ago=0.1, reply_to=1, references=[1, 10]))

    await read_again(factories, engine)

    [joined] = [c for c in await list_chains(anna) if c["email_count"] == 3]
    location = await chain_location(anna, joined["id"])
    assert location["project"] == {"id": purchase["id"], "name": PURCHASE}
    assert location["placement"] == by_rule(SUBJECT, "мониторы")
    assert chain_in_tree(await open_project(anna, renovation["id"]), ESTIMATE) is None


async def test_fr42_a_placement_by_hand_wins_over_a_rules_whatever_the_dates(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-42 «A placement by hand over a rule's»: the rule placed first, the hand later
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    await create_rule(anna, SUBJECT, "смета", renovation["id"])
    put(reader, letter(1, ESTIMATE, now, days_ago=5))
    put(reader, letter(10, MONITORS, now, days_ago=4, sender="sales@tech.example"))
    await read_again(factories)
    estimate = await chain_location(anna, await chain_id_of(anna, ESTIMATE))
    assert estimate["project"] == {"id": renovation["id"], "name": RENOVATION}
    assert estimate["placement"]["kind"] == "rule"
    factories.clock.advance(timedelta(days=1))
    await move_chain(anna, await chain_id_of(anna, MONITORS), purchase["id"])
    put(reader, letter(20, "Re: " + ESTIMATE, now, days_ago=0.1, reply_to=1, references=[1, 10]))

    await read_again(factories)

    [joined] = [c for c in await list_chains(anna) if c["email_count"] == 3]
    location = await chain_location(anna, joined["id"])
    assert location["project"] == {"id": purchase["id"], "name": PURCHASE}
    assert location["placement"] == MANUAL


async def joined_location(anna: AsyncClient) -> dict[str, Any]:
    """The location of the one chain of Анна that holds three emails."""
    [joined] = [c for c in await list_chains(anna) if c["email_count"] == 3]
    return await chain_location(anna, joined["id"])


async def test_fr42_a_rule_placed_before_the_engines_wins_when_joined(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-42: whatever their dates, the rule placed first, the engine later
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    await create_rule(anna, SUBJECT, "смета", renovation["id"])
    put(reader, letter(1, ESTIMATE, now, days_ago=5))
    put(reader, letter(10, MONITORS, now, days_ago=4, sender="sales@tech.example", text="Закупка"))
    await read_again(factories)
    factories.clock.advance(timedelta(days=1))
    engine = FakePlacementEngine("fake-1", {"закупка": 0.5})
    use_engine(factories.app, engine)
    await fill_project(anna, purchase["id"])
    monitors = await chain_location(anna, await chain_id_of(anna, MONITORS))
    assert monitors["placement"] == by_engine("fake-1", 0.5)
    put(reader, letter(20, "Re: " + ESTIMATE, now, days_ago=0.1, reply_to=1, references=[1, 10]))

    await read_again(factories, engine)

    location = await joined_location(anna)
    assert location["project"] == {"id": renovation["id"], "name": RENOVATION}
    assert location["placement"] == by_rule(SUBJECT, "смета")


async def test_fr42_a_placement_by_hand_made_before_a_rules_wins_when_joined(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-42: whatever their dates, the hand placed first, the rule later
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    put(reader, letter(10, MONITORS, now, days_ago=4, sender="sales@tech.example"))
    await read_again(factories)
    await move_chain(anna, await chain_id_of(anna, MONITORS), purchase["id"])
    factories.clock.advance(timedelta(days=1))
    await create_rule(anna, SUBJECT, "смета", renovation["id"])
    put(reader, letter(1, ESTIMATE, now, days_ago=3))
    await read_again(factories)
    estimate = await chain_location(anna, await chain_id_of(anna, ESTIMATE))
    assert estimate["placement"] == by_rule(SUBJECT, "смета")
    put(reader, letter(20, "Re: " + ESTIMATE, now, days_ago=0.1, reply_to=1, references=[1, 10]))

    await read_again(factories)

    location = await joined_location(anna)
    assert location["project"] == {"id": purchase["id"], "name": PURCHASE}
    assert location["placement"] == MANUAL


async def test_fr42_two_chains_placed_by_rules_keep_the_earlier_placement_when_joined(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-42: among placements of one kind it keeps the earliest
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    await create_rule(anna, SUBJECT, "смета", renovation["id"])
    put(reader, letter(1, ESTIMATE, now, days_ago=5))
    await read_again(factories)
    factories.clock.advance(timedelta(days=1))
    await create_rule(anna, SUBJECT, "мониторы", purchase["id"])
    put(reader, letter(10, MONITORS, now, days_ago=4, sender="sales@tech.example"))
    await read_again(factories)
    put(reader, letter(20, "Re: " + ESTIMATE, now, days_ago=0.1, reply_to=1, references=[1, 10]))

    await read_again(factories)

    location = await joined_location(anna)
    assert location["project"] == {"id": renovation["id"], "name": RENOVATION}
    assert location["placement"] == by_rule(SUBJECT, "смета")
