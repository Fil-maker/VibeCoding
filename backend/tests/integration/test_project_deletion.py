"""FR-56 through the HTTP API: deleting a project.

Also the new scenarios of FR-41 «The chains of a deleted project are not taken again» and of FR-45
«The target project is deleted».
"""

from http import HTTPStatus

import httpx

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine
from tests.factories import (
    API,
    Factories,
    chain_id_of,
    chain_location,
    count_emails,
    create_rule,
    delete_project,
    delete_project_response,
    deletion_counts,
    list_chains,
    list_rules,
    move_chain,
    open_chain,
    project_threads,
)
from tests.hand_placement import (
    ACT,
    DESIGN,
    DISCOUNT,
    ESTIMATE,
    MANUAL,
    MONITORS,
    anna_with_chains,
    chain_in_tree,
)
from tests.project_trees import (
    PETROV_ADDRESS,
    PURCHASE,
    RENOVATION,
    UNKNOWN_ID,
    fill_project,
    letter,
    list_projects,
    open_project,
    placed_chains,
    put,
    threads_of,
    use_engine,
    vera_with_mailbox,
)
from tests.rule_support import (
    ADDRESS,
    DOMAIN,
    EXCLUDED,
    NONE_STATE,
    SUBJECT,
    TECHSNAB,
    anna_with_two_projects,
    apply_rule,
    apply_rule_response,
    by_engine,
    by_rule,
    read_again,
    rule_moves,
)

ENGINE = FakePlacementEngine("fake-1", {"смет": 0.5})
STROYMASTER = "stroymaster.example"


async def annas_renovation_with_five_chains_and_two_rules(
    factories: Factories, reader: FakeMailReader
) -> tuple[httpx.AsyncClient, dict[str, str], list[dict[str, str]]]:
    """Анна: «Ремонт офиса» with 4 chains in threads, 1 in «Неразобранное», 2 rules to it."""
    anna = await anna_with_chains(factories, reader, [ESTIMATE, ACT, DESIGN, MONITORS, DISCOUNT])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    for subject, thread in [(ESTIMATE, "Смета"), (ACT, "Акты"), (DESIGN, "Дизайн")]:
        await move_chain(
            anna, await chain_id_of(anna, subject), renovation["id"], new_thread_name=thread
        )
    await move_chain(
        anna, await chain_id_of(anna, MONITORS), renovation["id"], new_thread_name="Акты"
    )
    await move_chain(anna, await chain_id_of(anna, DISCOUNT), renovation["id"])
    rules = [
        await create_rule(anna, DOMAIN, STROYMASTER, renovation["id"], "Смета"),
        await create_rule(anna, SUBJECT, "дизайн", renovation["id"]),
    ]
    return anna, renovation, rules


# --- FR-56 Delete a project ---


async def test_fr56_deleting_counts_the_chains_and_the_rules_and_removes_them(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-56 «Deleting a project»
    anna, renovation, rules = await annas_renovation_with_five_chains_and_two_rules(
        factories, reader
    )
    tree = await open_project(anna, renovation["id"])
    assert len(placed_chains(tree)) == 4  # 4 chains in threads ...
    assert len(tree["unassigned"]) == 1  # ... and 1 in «Неразобранное»
    threads = await project_threads(anna, renovation["id"])
    assert len(threads) == len(threads_of(tree)) > 0  # the threads set up above

    assert await deletion_counts(anna, renovation["id"]) == {"chain_count": 5, "rule_count": 2}

    await delete_project(anna, renovation["id"])

    assert await list_projects(anna) == []
    assert (
        await anna.get(f"{API}/projects/{renovation['id']}")
    ).status_code == HTTPStatus.NOT_FOUND
    # its threads are gone with it
    gone = await anna.get(f"{API}/projects/{renovation['id']}/threads")
    assert gone.status_code == HTTPStatus.NOT_FOUND
    listed = {rule["id"] for rule in await list_rules(anna)}
    assert listed.isdisjoint(rule["id"] for rule in rules)
    assert await list_rules(anna) == []


async def test_fr56_the_chains_of_a_deleted_project_are_taken_out_by_hand_with_their_emails(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-56 «The chains of a deleted project»
    anna = await anna_with_chains(factories, reader, [ESTIMATE, ACT, DESIGN])
    use_engine(factories.app, ENGINE)
    renovation = await factories.create_project(anna, RENOVATION, "Смета на ремонт")
    await fill_project(anna, renovation["id"])  # «Смета на ремонт офиса» by the engine
    estimate_id = await chain_id_of(anna, ESTIMATE)
    assert (await chain_location(anna, estimate_id))["placement"] == by_engine("fake-1", 0.5)
    act_id = await chain_id_of(anna, ACT)
    await move_chain(anna, act_id, renovation["id"])  # by hand
    design_id = await chain_id_of(anna, DESIGN)
    rule = await create_rule(anna, SUBJECT, "дизайн", renovation["id"])
    assert await apply_rule(anna, rule["id"], [design_id]) == 1  # by a rule
    assert (await chain_location(anna, design_id))["placement"] == by_rule(SUBJECT, "дизайн")
    emails_before = await count_emails(anna)
    email_counts = {c["id"]: c["email_count"] for c in await list_chains(anna)}

    await delete_project(anna, renovation["id"])

    assert await count_emails(anna) == emails_before
    listed = {c["id"]: c for c in await list_chains(anna)}
    for chain_id, subject in [(estimate_id, ESTIMATE), (act_id, ACT), (design_id, DESIGN)]:
        assert listed[chain_id]["subject"] == subject
        assert listed[chain_id]["email_count"] == email_counts[chain_id]
        assert len((await open_chain(anna, chain_id))["emails"]) == email_counts[chain_id]
        assert await chain_location(anna, chain_id) == EXCLUDED


async def test_fr56_an_empty_project_is_deleted_with_zero_counts(factories: Factories) -> None:
    # FR-56 «An empty project»
    anna = await factories.signed_in(await factories.confirmed_user())
    vacation = await factories.create_project(anna, "Отпуск", "Отпуск в августе")

    assert await deletion_counts(anna, vacation["id"]) == {"chain_count": 0, "rule_count": 0}

    await delete_project(anna, vacation["id"])

    assert await list_projects(anna) == []


async def test_fr56_the_name_of_a_deleted_project_is_free_again(factories: Factories) -> None:
    # FR-56 «The name is free again»
    anna = await factories.signed_in(await factories.confirmed_user())
    old = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    await delete_project(anna, old["id"])

    new = await factories.create_project(anna, RENOVATION, "Ремонт офиса")

    assert new["id"] != old["id"]
    tree = await open_project(anna, new["id"])
    assert tree["name"] == RENOVATION
    assert tree["filled"] is False
    assert (tree["counterparties"], tree["unassigned"]) == ([], [])


async def test_fr56_a_deleted_project_is_not_found(factories: Factories) -> None:
    # FR-56 «A deleted project»
    anna = await factories.signed_in(await factories.confirmed_user())
    project = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    await delete_project(anna, project["id"])

    opened = await anna.get(f"{API}/projects/{project['id']}")
    deleted_again = await delete_project_response(anna, project["id"])
    counted = await anna.get(f"{API}/projects/{project['id']}/deletion")

    for response in (opened, deleted_again, counted):
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["error"]["code"] == "not_found"


async def test_fr56_an_unknown_project_is_not_found(factories: Factories) -> None:
    # FR-21: an identifier that never existed is «not found»
    anna = await factories.signed_in(await factories.confirmed_user())

    deleted = await delete_project_response(anna, UNKNOWN_ID)
    counted = await anna.get(f"{API}/projects/{UNKNOWN_ID}/deletion")

    for response in (deleted, counted):
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["error"]["code"] == "not_found"


async def test_fr56_another_users_project_cannot_be_deleted_or_counted(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-56 «Another user's project»
    anna, renovation, rules = await annas_renovation_with_five_chains_and_two_rules(
        factories, reader
    )
    tree_before = await open_project(anna, renovation["id"])
    rules_before = await list_rules(anna)
    estimate_id = await chain_id_of(anna, ESTIMATE)
    location_before = await chain_location(anna, estimate_id)
    vera = await vera_with_mailbox(factories)

    deleted = await delete_project_response(vera, renovation["id"])
    counted = await vera.get(f"{API}/projects/{renovation['id']}/deletion")

    for response in (deleted, counted):
        assert response.status_code == HTTPStatus.NOT_FOUND
        assert response.json()["error"]["code"] == "not_found"
    assert await open_project(anna, renovation["id"]) == tree_before
    assert await list_rules(anna) == rules_before
    assert len(rules_before) == len(rules)
    assert await chain_location(anna, estimate_id) == location_before


async def test_fr56_deleting_needs_a_signed_in_user_and_a_matching_origin(
    factories: Factories, client: httpx.AsyncClient
) -> None:
    # FR-17 (a signed-in user only) and FR-20 (a matching Origin) on the routes of FR-56
    anna = await factories.signed_in(await factories.confirmed_user())
    project = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    attacker = await factories.open_client(origin="http://attacker.test")
    attacker.cookies.set("vc_session", anna.cookies["vc_session"])
    url = f"{API}/projects/{project['id']}"

    anonymous_delete = await client.delete(url)
    anonymous_count = await client.get(f"{url}/deletion")
    foreign = await attacker.delete(url)

    assert anonymous_delete.status_code == HTTPStatus.UNAUTHORIZED
    assert anonymous_count.status_code == HTTPStatus.UNAUTHORIZED
    assert foreign.status_code == HTTPStatus.FORBIDDEN
    assert foreign.json()["error"]["code"] == "forbidden_origin"
    assert [p["id"] for p in await list_projects(anna)] == [project["id"]]


# --- FR-41 The chains of a deleted project are not taken again ---


async def test_fr41_the_chains_of_a_deleted_project_are_not_taken_again(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-41 «The chains of a deleted project are not taken again»
    anna = await anna_with_chains(factories, reader, [ESTIMATE])
    use_engine(factories.app, ENGINE)
    renovation = await factories.create_project(anna, RENOVATION, "Смета на ремонт")
    await fill_project(anna, renovation["id"])
    estimate_id = await chain_id_of(anna, ESTIMATE)
    assert (await chain_location(anna, estimate_id))["state"] == "placed"
    await delete_project(anna, renovation["id"])

    purchase = await factories.create_project(anna, PURCHASE, ESTIMATE)
    filled = await fill_project(anna, purchase["id"])
    assert chain_in_tree(filled, ESTIMATE) is None
    [before] = [c for c in await list_chains(anna) if c["id"] == estimate_id]
    put(
        reader,
        letter(30, "Re: " + ESTIMATE, factories.clock.now(), days_ago=0.1, reply_to=1),
    )
    await read_again(factories, ENGINE)
    rule = await create_rule(anna, ADDRESS, PETROV_ADDRESS, purchase["id"])

    [after] = [c for c in await list_chains(anna) if c["id"] == estimate_id]
    assert after["email_count"] == before["email_count"] + 1  # the reply joined the chain
    assert await chain_location(anna, estimate_id) == EXCLUDED
    assert chain_in_tree(await open_project(anna, purchase["id"]), ESTIMATE) is None
    assert await rule_moves(anna, rule["id"]) == []
    await apply_rule_response(anna, rule["id"], [estimate_id])  # a rule never places it either
    assert await chain_location(anna, estimate_id) == EXCLUDED
    assert chain_in_tree(await open_project(anna, purchase["id"]), ESTIMATE) is None

    location = await move_chain(anna, estimate_id, purchase["id"])

    assert location["state"] == "placed"
    assert location["project"] == {"id": purchase["id"], "name": PURCHASE}
    assert location["placement"] == MANUAL


# --- FR-45 The target project is deleted ---


async def test_fr45_the_rules_of_a_deleted_target_project_go_with_it(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-45 «The target project is deleted»
    anna, renovation, purchase = await anna_with_two_projects(factories)
    await create_rule(anna, DOMAIN, STROYMASTER, renovation["id"])
    await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])

    await delete_project(anna, renovation["id"])

    rules = await list_rules(anna)
    assert [
        (r["condition"], r["value"], r["project"]["name"], r["thread_name"]) for r in rules
    ] == [(DOMAIN, TECHSNAB, PURCHASE, None)]
    put(reader, letter(40, "Новый счёт", factories.clock.now(), days_ago=0.1))
    await read_again(factories)
    new_id = await chain_id_of(anna, "Новый счёт")
    assert await chain_location(anna, new_id) == NONE_STATE
