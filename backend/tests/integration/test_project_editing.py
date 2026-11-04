"""FR-55 through the HTTP API: editing the name and the description of a project."""

from datetime import timedelta
from http import HTTPStatus

import httpx
import pytest

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine
from tests.factories import (
    API,
    Factories,
    chain_id_of,
    chain_location,
    create_rule,
    list_rules,
    update_project,
    update_project_response,
)
from tests.hand_placement import DISCOUNT, ESTIMATE, anna_with_chains, chain_in_tree
from tests.project_trees import (
    PURCHASE,
    RENOVATION,
    UNKNOWN_ID,
    fill_project,
    list_projects,
    open_project,
    tree_snapshot,
    use_engine,
    vera_with_mailbox,
)
from tests.rule_support import DOMAIN

PROJECT_EXISTS = "Проект с таким названием уже есть"
NEW_DESCRIPTION = "Ремонт офиса на Лесной: смета и акты"
DESCRIPTION = "Смета и скидки"
# «смет» is sure (0.4) and «скидк» unsure (0.2); «ремонт» appears only in NEW_DESCRIPTION: 0.6.
ENGINE = FakePlacementEngine("fake-1", {"смет": 0.4, "скидк": 0.2, "ремонт": 0.6})


async def anna_with_filled_renovation(
    factories: Factories, reader: FakeMailReader
) -> tuple[httpx.AsyncClient, dict[str, str], str]:
    """Анна with «Ремонт офиса» filled: the estimate in a thread, the discount in «Неразобранное».

    Returns the client, the project and the id of the estimate chain.
    """
    anna = await anna_with_chains(factories, reader, [ESTIMATE, DISCOUNT])
    use_engine(factories.app, ENGINE)
    renovation = await factories.create_project(anna, RENOVATION, DESCRIPTION)
    tree = await fill_project(anna, renovation["id"])
    assert [c["subject"] for c in tree["unassigned"]] == [DISCOUNT]
    assert chain_in_tree(tree, ESTIMATE) is not None
    chain_id = await chain_id_of(anna, ESTIMATE)
    assert (await chain_location(anna, chain_id))["thread"] is not None
    factories.clock.advance(timedelta(minutes=5))  # every edit comes after the filling
    return anna, renovation, chain_id


async def test_fr55_renaming_a_project_shows_the_new_name_everywhere(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-55 «Renaming a project»
    anna, renovation, chain_id = await anna_with_filled_renovation(factories, reader)
    rule = await create_rule(anna, DOMAIN, "stroymaster.example", renovation["id"], "Смета")

    tree = await update_project(anna, renovation["id"], "Ремонт офиса на Лесной", DESCRIPTION)

    assert tree["name"] == "Ремонт офиса на Лесной"
    assert [p["name"] for p in await list_projects(anna)] == ["Ремонт офиса на Лесной"]
    [listed] = await list_rules(anna)
    assert listed["id"] == rule["id"]
    assert (listed["condition"], listed["value"]) == (DOMAIN, "stroymaster.example")
    assert listed["project"] == {"id": renovation["id"], "name": "Ремонт офиса на Лесной"}
    assert listed["thread_name"] == "Смета"
    location = await chain_location(anna, chain_id)
    assert location["project"] == {"id": renovation["id"], "name": "Ремонт офиса на Лесной"}


async def test_fr55_changing_only_the_letter_case_is_saved(factories: Factories) -> None:
    # FR-55 «Changing only the letter case»
    anna = await factories.signed_in(await factories.confirmed_user())
    project = await factories.create_project(anna, RENOVATION, "Ремонт офиса")

    tree = await update_project(anna, project["id"], "ремонт офиса", "Ремонт офиса")

    assert tree["name"] == "ремонт офиса"
    assert (await open_project(anna, project["id"]))["name"] == "ремонт офиса"
    assert [p["name"] for p in await list_projects(anna)] == ["ремонт офиса"]


async def test_fr55_a_name_of_another_project_is_refused(factories: Factories) -> None:
    # FR-55 «A name of another project»
    anna = await factories.signed_in(await factories.confirmed_user())
    await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    purchase = await factories.create_project(anna, PURCHASE, "Закупка техники")

    response = await update_project_response(anna, purchase["id"], "РЕМОНТ ОФИСА", "Закупка")

    assert response.status_code == HTTPStatus.CONFLICT
    error = response.json()["error"]
    assert (error["code"], error["message"]) == ("project_exists", PROJECT_EXISTS)
    tree = await open_project(anna, purchase["id"])
    assert (tree["name"], tree["description"]) == (PURCHASE, "Закупка техники")


@pytest.mark.parametrize(
    ("name", "description", "field", "message"),
    [
        ("   ", "Описание", "name", "Укажите название проекта"),
        ("я" * 101, "Описание", "name", "Название — не длиннее 100 символов"),
        ("Ремонт офиса", "  ", "description", "Опишите проект"),
        ("Ремонт офиса", "я" * 2001, "description", "Описание — не длиннее 2000 символов"),
    ],
)
async def test_fr55_empty_or_too_long_fields_are_refused_and_nothing_is_saved(
    factories: Factories, name: str, description: str, field: str, message: str
) -> None:
    # FR-55 «Empty or too long fields»
    anna = await factories.signed_in(await factories.confirmed_user())
    project = await factories.create_project(anna, RENOVATION, "Ремонт офиса")

    response = await update_project_response(anna, project["id"], name, description)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["fields"] == {field: message}
    tree = await open_project(anna, project["id"])
    assert (tree["name"], tree["description"]) == (RENOVATION, "Ремонт офиса")


async def test_fr55_a_changed_description_moves_nothing_and_shows_the_hint(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-55 «A changed description moves nothing»
    anna, renovation, chain_id = await anna_with_filled_renovation(factories, reader)
    before = await open_project(anna, renovation["id"])
    location_before = await chain_location(anna, chain_id)
    assert before["description_changed"] is False

    tree = await update_project(anna, renovation["id"], RENOVATION, NEW_DESCRIPTION)

    assert tree["description"] == NEW_DESCRIPTION
    assert [c["subject"] for c in tree["unassigned"]] == [DISCOUNT]
    assert chain_in_tree(tree, ESTIMATE) is not None
    assert tree["description_changed"] is True
    assert tree_snapshot(tree) == tree_snapshot(before)
    assert await chain_location(anna, chain_id) == location_before
    assert (await open_project(anna, renovation["id"]))["description_changed"] is True


async def test_fr55_the_hint_goes_after_filling(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-55 «The hint goes after filling»
    anna, renovation, _ = await anna_with_filled_renovation(factories, reader)
    await update_project(anna, renovation["id"], RENOVATION, NEW_DESCRIPTION)
    assert (await open_project(anna, renovation["id"]))["description_changed"] is True
    factories.clock.advance(timedelta(minutes=5))  # the new filling comes after the edit

    before = chain_in_tree(await open_project(anna, renovation["id"]), ESTIMATE)
    assert before is not None
    assert before["placement"]["similarity"] == 0.4  # placed by the old description

    tree = await fill_project(anna, renovation["id"])

    assert tree["description"] == NEW_DESCRIPTION
    placed = chain_in_tree(tree, ESTIMATE)
    assert placed is not None
    assert placed["placement"]["similarity"] == 0.6  # placed by the new description
    assert tree["description_changed"] is False
    assert (await open_project(anna, renovation["id"]))["description_changed"] is False


async def test_fr55_changing_only_the_name_or_saving_the_description_unchanged_shows_no_hint(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-55 «Only the name changed»
    anna, renovation, _ = await anna_with_filled_renovation(factories, reader)

    renamed = await update_project(anna, renovation["id"], "Ремонт на Лесной", DESCRIPTION)
    unchanged = await update_project(anna, renovation["id"], "Ремонт на Лесной", DESCRIPTION)
    padded = await update_project(anna, renovation["id"], "Ремонт на Лесной", f"  {DESCRIPTION}  ")

    assert renamed["description_changed"] is False
    assert unchanged["description_changed"] is False
    assert padded["description_changed"] is False
    assert (await open_project(anna, renovation["id"]))["description_changed"] is False


async def test_fr55_an_unfilled_project_shows_no_hint_after_a_new_description(
    factories: Factories,
) -> None:
    # FR-55 «An unfilled project»
    anna = await factories.signed_in(await factories.confirmed_user())
    vacation = await factories.create_project(anna, "Отпуск", "Отпуск в августе")

    tree = await update_project(anna, vacation["id"], "Отпуск", "Отпуск в сентябре")

    assert tree["description"] == "Отпуск в сентябре"
    assert tree["filled"] is False
    assert tree["description_changed"] is False
    assert (await open_project(anna, vacation["id"]))["description_changed"] is False


async def test_fr55_another_users_project_cannot_be_changed(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-55 «Another user's project»
    anna, renovation, _ = await anna_with_filled_renovation(factories, reader)
    before = await open_project(anna, renovation["id"])
    vera = await vera_with_mailbox(factories)

    response = await update_project_response(vera, renovation["id"], "Чужое", "Чужое описание")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["error"]["code"] == "not_found"
    assert await open_project(anna, renovation["id"]) == before


async def test_fr55_an_unknown_project_is_not_found(factories: Factories) -> None:
    # FR-21: a project that does not exist is «not found»
    anna = await factories.signed_in(await factories.confirmed_user())

    response = await update_project_response(anna, UNKNOWN_ID, "Имя", "Описание")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["error"]["code"] == "not_found"


async def test_fr55_editing_needs_a_signed_in_user_and_a_matching_origin(
    factories: Factories, client: httpx.AsyncClient
) -> None:
    # FR-17 (a signed-in user only) and FR-20 (a matching Origin) on the route of FR-55
    anna = await factories.signed_in(await factories.confirmed_user())
    project = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    attacker = await factories.open_client(origin="http://attacker.test")
    attacker.cookies.set("vc_session", anna.cookies["vc_session"])
    body = {"name": "Взлом", "description": "Взлом"}

    anonymous = await client.patch(f"{API}/projects/{project['id']}", json=body)
    foreign = await attacker.patch(f"{API}/projects/{project['id']}", json=body)

    assert anonymous.status_code == HTTPStatus.UNAUTHORIZED
    assert anonymous.json()["error"]["code"] == "not_signed_in"
    assert foreign.status_code == HTTPStatus.FORBIDDEN
    assert foreign.json()["error"]["code"] == "forbidden_origin"
    assert (await open_project(anna, project["id"]))["name"] == RENOVATION
