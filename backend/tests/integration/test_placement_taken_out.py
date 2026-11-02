"""FR-41 (and FR-35 «Chains taken out are not taken») through the HTTP API: taking chains out."""

from datetime import timedelta
from http import HTTPStatus

import httpx

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine
from tests.factories import (
    API,
    Factories,
    chain_id_of,
    chain_location,
    list_chains,
    move_chain,
    take_out_chain,
    take_out_chain_response,
)
from tests.hand_placement import (
    DISCOUNT,
    ESTIMATE,
    MANUAL,
    anna_with_chains,
    chain_in_tree,
)
from tests.project_trees import (
    PURCHASE,
    RENOVATION,
    VERA_LOGIN,
    fill_project,
    letter,
    open_project,
    put,
    use_engine,
    vera_with_mailbox,
)

EXCLUDED = {"state": "excluded", "project": None, "thread": None, "placement": None}
NONE = {"state": "none", "project": None, "thread": None, "placement": None}
NOT_IN_PROJECT = "Цепочка не входит ни в один проект"
# «скидк» is unsure (0.2 between the thresholds 0.15 and 0.3), «смет» is sure.
ENGINE = FakePlacementEngine("fake-1", {"скидк": 0.2, "смет": 0.5})


async def anna_with_discount_in_unassigned(
    factories: Factories, reader: FakeMailReader
) -> tuple[httpx.AsyncClient, dict[str, str], str]:
    """Анна, «Ремонт офиса» filled with the discount chain in its «Неразобранное»."""
    anna = await anna_with_chains(factories, reader, [DISCOUNT, ESTIMATE])
    use_engine(factories.app, ENGINE)
    renovation = await factories.create_project(anna, RENOVATION, "Смета и скидки")
    await fill_project(anna, renovation["id"])
    discount_id = await chain_id_of(anna, DISCOUNT)
    assert (await chain_location(anna, discount_id))["thread"] is None
    return anna, renovation, discount_id


async def test_fr41_taking_a_chain_out_leaves_it_in_no_project(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-41 «Taking a chain out»
    anna, renovation, discount_id = await anna_with_discount_in_unassigned(factories, reader)

    location = await take_out_chain(anna, discount_id)

    assert location == EXCLUDED
    assert await chain_location(anna, discount_id) == EXCLUDED
    assert chain_in_tree(await open_project(anna, renovation["id"]), DISCOUNT) is None


async def test_fr41_the_engine_does_not_take_a_chain_back_on_filling_or_new_emails(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-41 «The engine does not take it back»
    anna, renovation, discount_id = await anna_with_discount_in_unassigned(factories, reader)
    await take_out_chain(anna, discount_id)
    now = factories.clock.now()
    [before] = [c for c in await list_chains(anna) if c["id"] == discount_id]

    await fill_project(anna, renovation["id"])
    put(reader, letter(30, "Re: " + DISCOUNT, now, days_ago=0.1, text="Скидка", reply_to=1))
    factories.clock.advance(timedelta(minutes=5))
    await factories.read_due(FakePlacementEngine("fake-2", {"скидк": 0.9}))

    [discount] = [c for c in await list_chains(anna) if c["id"] == discount_id]
    assert discount["email_count"] == before["email_count"] + 1  # the reply joined the chain
    assert await chain_location(anna, discount_id) == EXCLUDED
    assert chain_in_tree(await open_project(anna, renovation["id"]), DISCOUNT) is None


async def test_fr41_a_taken_out_chain_can_be_placed_back_by_hand(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-41 «Placing it back by hand»
    anna, renovation, discount_id = await anna_with_discount_in_unassigned(factories, reader)
    await take_out_chain(anna, discount_id)

    location = await move_chain(anna, discount_id, renovation["id"])

    assert location["state"] == "placed"
    assert location["thread"] is None
    assert location["placement"] == MANUAL
    tree = await open_project(anna, renovation["id"])
    assert [c["id"] for c in tree["unassigned"]] == [discount_id]


async def test_fr41_taking_out_a_chain_in_no_project_or_already_out_is_refused(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-41 «Taking out a chain in no project»
    anna, _, discount_id = await anna_with_discount_in_unassigned(factories, reader)
    in_no_project = await chain_id_of(anna, ESTIMATE)
    await take_out_chain(anna, in_no_project)  # placed by the engine, now out
    await take_out_chain(anna, discount_id)

    already_out = await take_out_chain_response(anna, discount_id)

    assert already_out.status_code == HTTPStatus.CONFLICT
    assert already_out.json()["error"]["code"] == "chain_not_in_project"
    assert already_out.json()["error"]["message"] == NOT_IN_PROJECT
    assert await chain_location(anna, discount_id) == EXCLUDED


async def test_fr41_a_chain_that_never_was_in_a_project_cannot_be_taken_out(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-41 «Taking out a chain in no project»
    anna = await anna_with_chains(factories, reader, [DISCOUNT])
    discount_id = await chain_id_of(anna, DISCOUNT)

    response = await take_out_chain_response(anna, discount_id)

    assert response.status_code == HTTPStatus.CONFLICT
    assert response.json()["error"]["code"] == "chain_not_in_project"
    assert response.json()["error"]["message"] == NOT_IN_PROJECT
    assert await chain_location(anna, discount_id) == NONE


async def test_fr41_another_users_chain_cannot_be_taken_out(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-41 «Another user's chain»
    anna, _, discount_id = await anna_with_discount_in_unassigned(factories, reader)
    before = await chain_location(anna, discount_id)
    vera = await vera_with_mailbox(factories)

    response = await take_out_chain_response(vera, discount_id)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["error"]["code"] == "not_found"
    assert await chain_location(anna, discount_id) == before


async def test_fr41_taking_a_chain_out_needs_a_matching_origin(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-41: a state-changing route needs a matching Origin
    anna, _, discount_id = await anna_with_discount_in_unassigned(factories, reader)
    before = await chain_location(anna, discount_id)
    stranger = await factories.open_client(origin="http://evil.test")
    stranger.cookies.update(anna.cookies)

    response = await stranger.delete(f"{API}/placements/{discount_id}")

    assert response.status_code == HTTPStatus.FORBIDDEN
    assert response.json()["error"]["code"] == "forbidden_origin"
    assert await chain_location(anna, discount_id) == before


async def test_fr35_a_chain_taken_out_is_not_taken_by_filling(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-35 «Chains taken out are not taken»
    anna = await anna_with_chains(factories, reader, [ESTIMATE])
    use_engine(factories.app, ENGINE)
    renovation = await factories.create_project(anna, RENOVATION, "Смета на ремонт")
    await fill_project(anna, renovation["id"])
    estimate_id = await chain_id_of(anna, ESTIMATE)
    await take_out_chain(anna, estimate_id)

    tree = await fill_project(anna, renovation["id"])
    purchase = await factories.create_project(anna, PURCHASE, "Смета на закупку")
    other_tree = await fill_project(anna, purchase["id"])

    assert chain_in_tree(tree, ESTIMATE) is None
    assert chain_in_tree(other_tree, ESTIMATE) is None
    assert await chain_location(anna, estimate_id) == EXCLUDED


async def test_fr41_a_vera_chain_is_not_touched_by_annas_take_out(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-41: taking out is per chain and per owner
    anna, _, discount_id = await anna_with_discount_in_unassigned(factories, reader)
    vera = await vera_with_mailbox(factories)
    now = factories.clock.now()
    put(reader, letter(80, DISCOUNT, now, days_ago=1, to=[VERA_LOGIN]), VERA_LOGIN)
    await factories.read_due()
    veras_id = await chain_id_of(vera, DISCOUNT)
    veras_project = await factories.create_project(vera, RENOVATION, "Ремонт офиса")
    await move_chain(vera, veras_id, veras_project["id"])
    veras_before = await chain_location(vera, veras_id)
    assert veras_before["state"] == "placed"

    await take_out_chain(anna, discount_id)

    assert await chain_location(vera, veras_id) == veras_before
