"""FR-32, FR-33 through the HTTP API: creating and listing projects."""

from http import HTTPStatus

import pytest
from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine
from tests.factories import API, VERA_EMAIL, Factories
from tests.project_trees import (
    CONFERENCE,
    DEMO_PROJECTS,
    RENOVATION,
    UNKNOWN_ID,
    fill_project,
    letter,
    list_projects,
    open_project,
    put,
    signed_in_with_mailbox,
    use_engine,
)

PROJECT_EXISTS = "Проект с таким названием уже есть"


async def anna_signed_in(factories: Factories) -> AsyncClient:
    """Анна signed in, without mailboxes."""
    return await factories.signed_in(await factories.confirmed_user())


async def post_project(client: AsyncClient, name: str, description: str) -> HTTPStatus:
    """POST /projects; returns the status only."""
    response = await client.post(f"{API}/projects", json={"name": name, "description": description})
    return HTTPStatus(response.status_code)


# --- FR-32 Create a project ---


async def test_fr32_a_new_project_is_created_empty(factories: Factories) -> None:
    # FR-32 «A new project»
    anna = await anna_signed_in(factories)

    response = await anna.post(
        f"{API}/projects", json={"name": RENOVATION, "description": DEMO_PROJECTS[RENOVATION]}
    )

    assert response.status_code == HTTPStatus.CREATED
    summary = response.json()
    assert set(summary) == {"id", "name", "filled", "placed_count", "unassigned_count"}
    assert summary["name"] == RENOVATION
    assert summary["filled"] is False
    assert (summary["placed_count"], summary["unassigned_count"]) == (0, 0)
    tree = await open_project(anna, summary["id"])
    assert tree["name"] == RENOVATION
    assert tree["description"] == DEMO_PROJECTS[RENOVATION]
    assert tree["filled"] is False
    assert (tree["counterparties"], tree["unassigned"]) == ([], [])


async def test_fr32_leading_and_trailing_spaces_are_dropped(factories: Factories) -> None:
    # FR-32: leading and trailing spaces are dropped
    anna = await anna_signed_in(factories)

    project = await factories.create_project(anna, "  Ремонт офиса  ", "  Смета и акты \n")

    tree = await open_project(anna, project["id"])
    assert (tree["name"], tree["description"]) == ("Ремонт офиса", "Смета и акты")


@pytest.mark.parametrize(
    ("name", "description", "field", "message"),
    [
        ("   ", "Описание", "name", "Укажите название проекта"),
        ("я" * 101, "Описание", "name", "Название — не длиннее 100 символов"),
        ("Ремонт офиса", "  ", "description", "Опишите проект"),
        ("Ремонт офиса", "я" * 2001, "description", "Описание — не длиннее 2000 символов"),
    ],
)
async def test_fr32_empty_or_too_long_fields_are_refused_and_nothing_is_saved(
    factories: Factories, name: str, description: str, field: str, message: str
) -> None:
    # FR-32 «Empty or too long fields»
    anna = await anna_signed_in(factories)

    response = await anna.post(f"{API}/projects", json={"name": name, "description": description})

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["fields"] == {field: message}
    assert await list_projects(anna) == []


async def test_fr32_a_name_of_100_and_a_description_of_2000_characters_are_accepted(
    factories: Factories,
) -> None:
    # FR-32: a name of 1 to 100 characters and a description of 1 to 2000 characters
    anna = await anna_signed_in(factories)

    assert await post_project(anna, "я" * 100, "я" * 2000) == HTTPStatus.CREATED
    assert await post_project(anna, "Я", "я") == HTTPStatus.CREATED


async def test_fr32_the_same_name_in_another_case_is_refused(factories: Factories) -> None:
    # FR-32 «The same name twice»
    anna = await anna_signed_in(factories)
    first = await factories.create_project(anna, RENOVATION, DEMO_PROJECTS[RENOVATION])

    response = await anna.post(
        f"{API}/projects", json={"name": "ремонт офиса", "description": "Другое описание"}
    )

    assert response.status_code == HTTPStatus.CONFLICT
    error = response.json()["error"]
    assert (error["code"], error["message"]) == ("project_exists", PROJECT_EXISTS)
    assert [p["id"] for p in await list_projects(anna)] == [first["id"]]


async def test_fr32_another_user_may_have_the_same_name(factories: Factories) -> None:
    # FR-32 «Another user has the same name»
    anna = await anna_signed_in(factories)
    annas = await factories.create_project(anna, RENOVATION, DEMO_PROJECTS[RENOVATION])
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))

    status = await post_project(vera, RENOVATION, "Ремонт квартиры")

    assert status == HTTPStatus.CREATED
    assert [(p["id"], p["name"]) for p in await list_projects(anna)] == [(annas["id"], RENOVATION)]


async def test_project_routes_need_a_signed_in_user(
    factories: Factories, client: AsyncClient
) -> None:
    # design «Interface»: every route needs a signed-in user
    await factories.confirmed_user()

    responses = [
        await client.get(f"{API}/projects"),
        await client.post(f"{API}/projects", json={"name": "П", "description": "О"}),
        await client.get(f"{API}/projects/{UNKNOWN_ID}"),
        await client.post(f"{API}/projects/{UNKNOWN_ID}/fill"),
    ]

    assert [r.status_code for r in responses] == [HTTPStatus.UNAUTHORIZED] * 4
    assert {r.json()["error"]["code"] for r in responses} == {"not_signed_in"}


async def test_creating_or_filling_a_project_from_another_site_is_refused(
    factories: Factories,
) -> None:
    # design «Interface»: state-changing routes need a matching Origin
    anna = await anna_signed_in(factories)
    project = await factories.create_project(anna, RENOVATION, DEMO_PROJECTS[RENOVATION])
    attacker = await factories.open_client(origin="http://attacker.test")
    attacker.cookies.set("vc_session", anna.cookies["vc_session"])

    responses = [
        await attacker.post(f"{API}/projects", json={"name": "П", "description": "О"}),
        await attacker.post(f"{API}/projects/{project['id']}/fill"),
    ]

    assert [r.status_code for r in responses] == [HTTPStatus.FORBIDDEN] * 2
    assert {r.json()["error"]["code"] for r in responses} == {"forbidden_origin"}
    assert [p["name"] for p in await list_projects(anna)] == [RENOVATION]
    assert (await open_project(anna, project["id"]))["filled"] is False


# --- FR-33 List the projects ---


async def test_fr33_projects_are_listed_by_name_with_their_counts(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-33 «The list of projects»
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    subjects = ["Смета: ремонт", "Акт: ремонт", "График: ремонт", "Офисная мебель"]
    subjects += ["ТехФорум: программа", "ТехФорум: доклад", "ТехФорум: стенд"]
    for number, subject in enumerate(subjects):
        put(reader, letter(number, subject, now, days_ago=10 - number))
    await factories.read_due()
    use_engine(
        factories.app,
        FakePlacementEngine("fake-1", {"ремонт": 0.5, "офис": 0.2, "техфорум": 0.6}),
    )
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    conference = await factories.create_project(anna, CONFERENCE, "Конференция ТехФорум")
    await fill_project(anna, renovation["id"])
    await fill_project(anna, conference["id"])

    projects = await list_projects(anna)

    assert [
        (p["name"], p["filled"], p["placed_count"], p["unassigned_count"]) for p in projects
    ] == [(CONFERENCE, True, 3, 0), (RENOVATION, True, 3, 1)]


async def test_fr33_a_user_without_projects_gets_an_empty_list(factories: Factories) -> None:
    # FR-33 «No projects yet»
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))

    assert await list_projects(vera) == []


async def test_fr33_a_user_sees_only_their_own_projects(factories: Factories) -> None:
    # FR-33 «Only one's own projects»
    anna = await anna_signed_in(factories)
    await factories.create_project(anna, RENOVATION, DEMO_PROJECTS[RENOVATION])
    await factories.create_project(anna, CONFERENCE, DEMO_PROJECTS[CONFERENCE])
    vera = await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))
    veras = await factories.create_project(vera, "Отпуск", "Отпуск в августе")

    projects = await list_projects(vera)

    assert [(p["id"], p["name"]) for p in projects] == [(veras["id"], "Отпуск")]
