"""FR-47 request-level cases: changed before apply, twice, order, ids, ownership, validation."""

from http import HTTPStatus

from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from tests.factories import (
    API,
    Factories,
    chain_id_of,
    chain_location,
    create_rule,
    move_chain,
)
from tests.hand_placement import MANUAL, MONITORS
from tests.project_trees import (
    UNKNOWN_ID,
    open_project,
)
from tests.rule_support import (
    CONTRACT,
    DOMAIN,
    NONE_STATE,
    TECHSNAB,
    anna_with_two_projects,
    apply_rule,
    apply_rule_response,
    by_rule,
    project_ref,
    read_volkov_chains,
    rule_moves,
    rule_moves_response,
    vera_with_project,
)


async def test_fr47_a_chain_changed_before_apply_is_left_alone(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «Changed before «Применить»»
    anna, renovation, purchase = await anna_with_two_projects(factories)
    await read_volkov_chains(factories, reader, [MONITORS, CONTRACT])
    monitors_id = await chain_id_of(anna, MONITORS)
    contract_id = await chain_id_of(anna, CONTRACT)
    rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])
    assert {m["chain_id"] for m in await rule_moves(anna, rule["id"])} == {monitors_id, contract_id}
    await move_chain(anna, contract_id, renovation["id"])

    assert await apply_rule(anna, rule["id"], [monitors_id, contract_id]) == 1

    monitors = await chain_location(anna, monitors_id)
    assert monitors["project"] == project_ref(purchase)
    assert monitors["placement"] == by_rule(DOMAIN, TECHSNAB)
    contract = await chain_location(anna, contract_id)
    assert contract["project"] == project_ref(renovation)
    assert contract["placement"] == MANUAL


async def test_fr47_applying_twice_moves_nothing_the_second_time(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «Applied twice»
    anna, _, purchase = await anna_with_two_projects(factories)
    await read_volkov_chains(factories, reader, [MONITORS])
    chain_id = await chain_id_of(anna, MONITORS)
    rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])
    assert await apply_rule(anna, rule["id"], [chain_id]) == 1
    tree = await open_project(anna, purchase["id"])
    location = await chain_location(anna, chain_id)

    assert await apply_rule(anna, rule["id"], [chain_id]) == 0

    assert await open_project(anna, purchase["id"]) == tree
    assert await chain_location(anna, chain_id) == location
    assert await rule_moves(anna, rule["id"]) == []


async def test_fr47_the_moves_are_newest_first_then_by_chain_id(
    factories: Factories, reader: FakeMailReader
) -> None:
    # design «Interface»: RuleMoves is newest latest_email_at first, then chain_id
    anna, _, purchase = await anna_with_two_projects(factories)
    await read_volkov_chains(factories, reader, [MONITORS, CONTRACT, "Счёт на серверы"])
    newest = await chain_id_of(anna, "Счёт на серверы")
    rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])

    moves = await rule_moves(anna, rule["id"])

    assert [m["subject"] for m in moves] == ["Счёт на серверы", CONTRACT, MONITORS]
    assert moves[0]["chain_id"] == newest
    assert [m["latest_email_at"] for m in moves] == sorted(
        (m["latest_email_at"] for m in moves), reverse=True
    )


async def test_fr47_duplicate_ids_are_ignored(factories: Factories, reader: FakeMailReader) -> None:
    # design «Interface»: RuleApply — duplicates ignored
    anna, _, purchase = await anna_with_two_projects(factories)
    await read_volkov_chains(factories, reader, [MONITORS])
    chain_id = await chain_id_of(anna, MONITORS)
    rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])

    assert await apply_rule(anna, rule["id"], [chain_id, chain_id]) == 1


async def test_fr47_an_unknown_chain_id_moves_nothing(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47: «Применить» places the listed chains that still qualify
    anna, _, purchase = await anna_with_two_projects(factories)
    await read_volkov_chains(factories, reader, [MONITORS])
    chain_id = await chain_id_of(anna, MONITORS)
    rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])

    assert await apply_rule(anna, rule["id"], [UNKNOWN_ID]) == 0
    assert await chain_location(anna, chain_id) == NONE_STATE


async def test_fr47_a_chain_missing_from_the_applied_ids_stays(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47: only the listed (sent) chains are placed
    anna, _, purchase = await anna_with_two_projects(factories)
    await read_volkov_chains(factories, reader, [MONITORS, CONTRACT])
    monitors_id = await chain_id_of(anna, MONITORS)
    contract_id = await chain_id_of(anna, CONTRACT)
    rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])

    assert await apply_rule(anna, rule["id"], [monitors_id]) == 1
    assert await chain_location(anna, contract_id) == NONE_STATE


async def test_fr47_another_users_rule_is_not_found_and_nothing_moves(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-47 «Another user's rule or chains»
    anna, _, purchase = await anna_with_two_projects(factories)
    await read_volkov_chains(factories, reader, [MONITORS])
    chain_id = await chain_id_of(anna, MONITORS)
    annas_rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])
    vera, veras_project = await vera_with_project(factories)
    veras_rule = await create_rule(vera, DOMAIN, TECHSNAB, veras_project["id"])

    responses = [
        await rule_moves_response(vera, annas_rule["id"]),
        await apply_rule_response(vera, annas_rule["id"], [chain_id]),
    ]

    assert [r.status_code for r in responses] == [HTTPStatus.NOT_FOUND] * 2
    assert {r.json()["error"]["code"] for r in responses} == {"not_found"}
    assert await chain_location(anna, chain_id) == NONE_STATE

    # her own rule naming the chain of Анна: the chain of Анна does not move
    own = await apply_rule_response(vera, veras_rule["id"], [chain_id])
    assert own.status_code == HTTPStatus.OK, own.text
    assert own.json() == {"moved": 0}
    assert await rule_moves(vera, veras_rule["id"]) == []
    assert await chain_location(anna, chain_id) == NONE_STATE
    assert (await open_project(vera, veras_project["id"]))["unassigned"] == []


async def test_fr47_an_unknown_rule_is_not_found(factories: Factories) -> None:
    anna, _, _ = await anna_with_two_projects(factories)

    responses = [
        await rule_moves_response(anna, UNKNOWN_ID),
        await apply_rule_response(anna, UNKNOWN_ID, []),
    ]

    assert [r.status_code for r in responses] == [HTTPStatus.NOT_FOUND] * 2
    assert {r.json()["error"]["code"] for r in responses} == {"not_found"}


async def test_fr47_a_malformed_apply_body_is_refused(factories: Factories) -> None:
    # design «Interface»: 422 validation_failed
    anna, _, purchase = await anna_with_two_projects(factories)
    rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])
    url = f"{API}/placements/by-rule/{rule['id']}"

    responses = [
        await anna.post(url, json={"chain_ids": ["not-a-uuid"]}),
        await anna.post(url, json={"chain_ids": [UNKNOWN_ID] * 5001}),
        await anna.post(url, json={}),
    ]

    assert [r.status_code for r in responses] == [HTTPStatus.UNPROCESSABLE_ENTITY] * 3
    assert {r.json()["error"]["code"] for r in responses} == {"validation_failed"}


async def test_fr47_the_routes_need_a_signed_in_user_and_the_right_origin(
    factories: Factories, client: AsyncClient
) -> None:
    # design «Interface»: 401 not_signed_in, 403 forbidden_origin on POST from another site
    anna, _, purchase = await anna_with_two_projects(factories)
    rule = await create_rule(anna, DOMAIN, TECHSNAB, purchase["id"])
    url = f"{API}/placements/by-rule/{rule['id']}"
    attacker = await factories.open_client(origin="http://attacker.test")
    attacker.cookies.set("vc_session", anna.cookies["vc_session"])

    anonymous = [await client.get(url), await client.post(url, json={"chain_ids": []})]
    foreign = await attacker.post(url, json={"chain_ids": []})

    assert [r.status_code for r in anonymous] == [HTTPStatus.UNAUTHORIZED] * 2
    assert {r.json()["error"]["code"] for r in anonymous} == {"not_signed_in"}
    assert foreign.status_code == HTTPStatus.FORBIDDEN
    assert foreign.json()["error"]["code"] == "forbidden_origin"
