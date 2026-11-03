"""FR-47 after a rule edit, and FR-45: an edit alone and a delete alone move nothing."""

from app.platform.mail_reader import FakeMailReader
from tests.factories import (
    Factories,
    chain_id_of,
    chain_location,
    create_rule,
    delete_rule,
    list_rules,
    project_threads,
    update_rule,
)
from tests.hand_placement import MONITORS
from tests.project_trees import (
    PETROV_ADDRESS,
    letter,
    open_project,
    put,
    thread_subjects,
)
from tests.rule_support import (
    ADDRESS,
    CONTRACT,
    DOMAIN,
    NONE_STATE,
    TECHSNAB,
    anna_with_two_projects,
    apply_rule,
    by_rule,
    project_ref,
    read_again,
    read_volkov_chains,
    rule_moves,
)


async def test_fr47_an_edited_target_moves_the_chains_the_rule_placed(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «An edited target»
    anna, renovation, purchase = await anna_with_two_projects(factories)
    rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])
    await read_volkov_chains(factories, reader, [MONITORS, CONTRACT])
    ids = [await chain_id_of(anna, MONITORS), await chain_id_of(anna, CONTRACT)]
    assert {c["subject"] for c in (await open_project(anna, purchase["id"]))["unassigned"]} == {
        MONITORS,
        CONTRACT,
    }

    await update_rule(anna, rule["id"], DOMAIN, TECHSNAB, renovation["id"], "Поставки")

    assert {m["chain_id"] for m in await rule_moves(anna, rule["id"])} == set(ids)
    assert await apply_rule(anna, rule["id"], ids) == 2
    assert thread_subjects(await open_project(anna, renovation["id"])) == {
        "Поставки": {MONITORS, CONTRACT}
    }
    for chain_id in ids:
        assert (await chain_location(anna, chain_id))["placement"] == by_rule(DOMAIN, TECHSNAB)
    assert (await open_project(anna, purchase["id"]))["unassigned"] == []


async def test_fr47_a_chain_the_edited_rule_no_longer_matches_stays(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «No longer matching after an edit»
    anna, _, purchase = await anna_with_two_projects(factories)
    rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])
    await read_volkov_chains(factories, reader, [MONITORS])
    chain_id = await chain_id_of(anna, MONITORS)
    before = await chain_location(anna, chain_id)

    await update_rule(anna, rule["id"], DOMAIN, "techsnab.ru", purchase["id"])

    assert await rule_moves(anna, rule["id"]) == []
    assert await apply_rule(anna, rule["id"], [chain_id]) == 0
    assert await chain_location(anna, chain_id) == before


async def test_fr45_an_edit_alone_leaves_the_chains_the_rule_placed_where_they_are(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-45 «Editing a rule»: until «Применить» the chains the rule placed stay
    anna, renovation, purchase = await anna_with_two_projects(factories)
    rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])
    await read_volkov_chains(factories, reader, [MONITORS, CONTRACT])
    ids = [await chain_id_of(anna, MONITORS), await chain_id_of(anna, CONTRACT)]
    before = [await chain_location(anna, chain_id) for chain_id in ids]
    assert [loc["project"] for loc in before] == [project_ref(purchase)] * 2
    assert [loc["placement"] for loc in before] == [by_rule(DOMAIN, TECHSNAB)] * 2

    await update_rule(anna, rule["id"], DOMAIN, TECHSNAB, renovation["id"], "Поставки")

    assert [await chain_location(anna, chain_id) for chain_id in ids] == before
    assert {c["subject"] for c in (await open_project(anna, purchase["id"]))["unassigned"]} == {
        MONITORS,
        CONTRACT,
    }
    assert await project_threads(anna, renovation["id"]) == []
    assert {m["chain_id"] for m in await rule_moves(anna, rule["id"])} == set(ids)


async def test_fr45_an_edit_alone_moves_a_chain_in_no_project_nowhere(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-45: editing a rule moves no chain, also one in no project
    anna, renovation, _ = await anna_with_two_projects(factories)
    await read_volkov_chains(factories, reader, [CONTRACT])
    chain_id = await chain_id_of(anna, CONTRACT)
    rule = await create_rule(anna, DOMAIN, "other.example", renovation["id"])

    await update_rule(anna, rule["id"], DOMAIN, TECHSNAB, renovation["id"], "Поставки")

    assert await chain_location(anna, chain_id) == NONE_STATE


async def test_fr45_a_delete_alone_changes_no_placement(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-45 «Deleting a rule»: the rule is unlisted, the chains it placed stay
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    rule = await create_rule(anna, ADDRESS, PETROV_ADDRESS, renovation["id"])
    put(reader, letter(1, "Смета на покраску стен", now, days_ago=1))
    await read_again(factories)
    chain_id = await chain_id_of(anna, "Смета на покраску стен")
    before = await chain_location(anna, chain_id)
    tree = await open_project(anna, renovation["id"])
    assert before["placement"] == by_rule(ADDRESS, PETROV_ADDRESS)

    await delete_rule(anna, rule["id"])

    assert await list_rules(anna) == []
    assert await chain_location(anna, chain_id) == before
    assert await open_project(anna, renovation["id"]) == tree
