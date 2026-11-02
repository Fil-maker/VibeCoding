"""FR-40 through the HTTP API: placing a chain by hand."""

from http import HTTPStatus

import pytest

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine
from tests.factories import (
    API,
    Factories,
    chain_id_of,
    chain_location,
    move_chain,
    move_chain_response,
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
    MONITORS_THREAD,
    anna_with_chains,
    chain_in_tree,
)
from tests.project_trees import (
    PURCHASE,
    RENOVATION,
    UNKNOWN_ID,
    VERA_LOGIN,
    fill_project,
    letter,
    open_project,
    put,
    thread_subjects,
    tree_snapshot,
    use_engine,
    vera_with_mailbox,
)


async def test_fr40_moving_a_chain_to_a_thread_of_another_project(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40 «Moving a chain to another project»
    anna = await anna_with_chains(factories, reader, [MONITORS, ACT])
    use_engine(factories.app, FakePlacementEngine("fake-1", {"монитор": 0.5}))
    renovation = await factories.create_project(anna, RENOVATION, "Мониторы в офис")
    purchase = await factories.create_project(anna, PURCHASE, "Закупка техники")
    await fill_project(anna, renovation["id"])
    act_id = await chain_id_of(anna, ACT)
    monitors_id = await chain_id_of(anna, MONITORS)
    assert chain_in_tree(await open_project(anna, renovation["id"]), MONITORS) is not None
    thread = (await move_chain(anna, act_id, purchase["id"], new_thread_name=MONITORS_THREAD))[
        "thread"
    ]

    location = await move_chain(anna, monitors_id, purchase["id"], thread_id=thread["id"])

    assert location == {
        "state": "placed",
        "project": {"id": purchase["id"], "name": PURCHASE},
        "thread": {"id": thread["id"], "name": MONITORS_THREAD},
        "placement": MANUAL,
    }
    assert await chain_location(anna, monitors_id) == location
    assert chain_in_tree(await open_project(anna, renovation["id"]), MONITORS) is None
    purchase_tree = await open_project(anna, purchase["id"])
    assert MONITORS in thread_subjects(purchase_tree)[MONITORS_THREAD]


async def test_fr40_placing_a_chain_of_no_project_into_unassigned(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40 «Placing a chain of no project»
    anna = await anna_with_chains(factories, reader, [DESIGN])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    design_id = await chain_id_of(anna, DESIGN)
    assert (await chain_location(anna, design_id))["state"] == "none"

    location = await move_chain(anna, design_id, renovation["id"])

    assert location == {
        "state": "placed",
        "project": {"id": renovation["id"], "name": RENOVATION},
        "thread": None,
        "placement": MANUAL,
    }
    tree = await open_project(anna, renovation["id"])
    assert [c["id"] for c in tree["unassigned"]] == [design_id]
    assert tree["unassigned"][0]["placement"] == MANUAL


async def test_fr40_a_new_thread_holds_the_moved_chain(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40 «A new thread»
    anna = await anna_with_chains(factories, reader, [ACT])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    act_id = await chain_id_of(anna, ACT)

    location = await move_chain(anna, act_id, renovation["id"], new_thread_name=ACTS_THREAD)

    assert location["thread"]["name"] == ACTS_THREAD
    threads = await project_threads(anna, renovation["id"])
    assert [t["name"] for t in threads] == [ACTS_THREAD]
    assert thread_subjects(await open_project(anna, renovation["id"])) == {ACTS_THREAD: {ACT}}


async def test_fr40_a_new_thread_name_is_stripped_and_100_characters_are_accepted(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40: a name of 1 to 100 characters, spaces at the ends dropped
    anna = await anna_with_chains(factories, reader, [ACT, DESIGN])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    long_name = "я" * 100

    first = await move_chain(
        anna, await chain_id_of(anna, ACT), renovation["id"], new_thread_name=f"  {ACTS_THREAD}  "
    )
    second = await move_chain(
        anna, await chain_id_of(anna, DESIGN), renovation["id"], new_thread_name=long_name
    )

    assert (first["thread"]["name"], second["thread"]["name"]) == (ACTS_THREAD, long_name)


async def test_fr40_a_one_character_thread_name_is_accepted(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40: the lower bound of a name of 1 to 100 characters
    anna = await anna_with_chains(factories, reader, [ACT])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")

    location = await move_chain(
        anna, await chain_id_of(anna, ACT), renovation["id"], new_thread_name="А"
    )

    assert location["thread"]["name"] == "А"
    assert [t["name"] for t in await project_threads(anna, renovation["id"])] == ["А"]


async def test_fr40_moving_into_the_engines_own_thread_pins_the_chain(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40 «Pinning the engine's place»
    anna = await anna_with_chains(factories, reader, [ESTIMATE])
    use_engine(factories.app, FakePlacementEngine("fake-1", {"смет": 0.5}))
    renovation = await factories.create_project(anna, RENOVATION, "Смета на ремонт")
    await fill_project(anna, renovation["id"])
    estimate_id = await chain_id_of(anna, ESTIMATE)
    [thread] = await project_threads(anna, renovation["id"])
    assert thread["name"] == ESTIMATE
    assert (await chain_location(anna, estimate_id))["placement"]["kind"] == "engine"

    location = await move_chain(anna, estimate_id, renovation["id"], thread_id=thread["id"])

    assert location["thread"] == thread
    assert location["placement"] == MANUAL
    assert await project_threads(anna, renovation["id"]) == [thread]


async def test_fr40_a_thread_left_without_chains_disappears(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40 «A thread left empty»
    anna = await anna_with_chains(factories, reader, [ACT])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    act_id = await chain_id_of(anna, ACT)
    await move_chain(anna, act_id, renovation["id"], new_thread_name=ACTS_THREAD)

    location = await move_chain(anna, act_id, renovation["id"])

    assert location["thread"] is None
    assert await project_threads(anna, renovation["id"]) == []


async def test_fr40_a_thread_disappears_when_its_chain_moves_to_another_thread_or_project(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40 «A thread left empty»: the chain leaves by a move into another thread / project
    anna = await anna_with_chains(factories, reader, [ACT, DESIGN])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    purchase = await factories.create_project(anna, PURCHASE, "Закупка техники")
    act_id = await chain_id_of(anna, ACT)
    design_id = await chain_id_of(anna, DESIGN)
    await move_chain(anna, act_id, renovation["id"], new_thread_name=ACTS_THREAD)
    kept = (await move_chain(anna, design_id, renovation["id"], new_thread_name="Дизайн"))["thread"]

    await move_chain(anna, act_id, renovation["id"], thread_id=kept["id"])

    assert await project_threads(anna, renovation["id"]) == [kept]
    await move_chain(anna, design_id, purchase["id"], new_thread_name="Другое")
    await move_chain(anna, act_id, purchase["id"])
    assert await project_threads(anna, renovation["id"]) == []


async def test_fr40_a_thread_disappears_when_its_chain_is_taken_out(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40 «A thread left empty»: the chain leaves by «Убрать из проекта»
    anna = await anna_with_chains(factories, reader, [ACT])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    act_id = await chain_id_of(anna, ACT)
    await move_chain(anna, act_id, renovation["id"], new_thread_name=ACTS_THREAD)

    await take_out_chain(anna, act_id)

    assert await project_threads(anna, renovation["id"]) == []


@pytest.mark.parametrize(
    ("name", "message"),
    [
        ("   ", "Укажите название ветки"),
        ("я" * 101, "Название ветки — не длиннее 100 символов"),
    ],
)
async def test_fr40_an_empty_or_too_long_thread_name_is_refused_and_nothing_changes(
    factories: Factories, reader: FakeMailReader, name: str, message: str
) -> None:
    # FR-40 «An empty or too long thread name»
    anna = await anna_with_chains(factories, reader, [ACT])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    act_id = await chain_id_of(anna, ACT)

    response = await move_chain_response(anna, act_id, renovation["id"], new_thread_name=name)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert list(error["fields"].values()) == [message]
    assert (await chain_location(anna, act_id))["state"] == "none"
    assert await project_threads(anna, renovation["id"]) == []


async def test_fr40_a_thread_and_a_new_thread_together_are_refused(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40: at most one of the thread and the new thread name
    anna = await anna_with_chains(factories, reader, [ACT, DESIGN])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    design_id = await chain_id_of(anna, DESIGN)
    thread = (await move_chain(anna, design_id, renovation["id"], new_thread_name="Дизайн"))[
        "thread"
    ]
    act_id = await chain_id_of(anna, ACT)

    response = await move_chain_response(
        anna, act_id, renovation["id"], thread_id=thread["id"], new_thread_name=ACTS_THREAD
    )

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert "Выберите либо ветку, либо новую ветку" in error["fields"].values()
    assert (await chain_location(anna, act_id))["state"] == "none"


async def test_fr40_a_thread_of_another_project_is_not_found_and_the_chain_stays(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40 «A thread of another project»
    anna = await anna_with_chains(factories, reader, [ACT, DESIGN])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    purchase = await factories.create_project(anna, PURCHASE, "Закупка техники")
    design_id = await chain_id_of(anna, DESIGN)
    foreign = (await move_chain(anna, design_id, purchase["id"], new_thread_name="Техника"))[
        "thread"
    ]
    act_id = await chain_id_of(anna, ACT)
    await move_chain(anna, act_id, renovation["id"])
    before = await chain_location(anna, act_id)

    response = await move_chain_response(anna, act_id, renovation["id"], thread_id=foreign["id"])

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["error"]["code"] == "not_found"
    assert await chain_location(anna, act_id) == before


async def test_fr40_a_missing_thread_or_project_is_not_found(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40: an identifier that names nothing answers «not found»
    anna = await anna_with_chains(factories, reader, [ACT])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    act_id = await chain_id_of(anna, ACT)

    no_thread = await move_chain_response(anna, act_id, renovation["id"], thread_id=UNKNOWN_ID)
    no_project = await move_chain_response(anna, act_id, UNKNOWN_ID)

    assert (no_thread.status_code, no_project.status_code) == (HTTPStatus.NOT_FOUND,) * 2
    assert (await chain_location(anna, act_id))["state"] == "none"


async def test_fr40_another_users_project_or_thread_is_not_found(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40 «Another user's project or thread»
    anna = await anna_with_chains(factories, reader, [ACT])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    act_id = await chain_id_of(anna, ACT)
    annas_thread = (await move_chain(anna, act_id, renovation["id"], new_thread_name=ACTS_THREAD))[
        "thread"
    ]
    annas_before = tree_snapshot(await open_project(anna, renovation["id"]))
    vera = await vera_with_mailbox(factories)
    now = factories.clock.now()
    put(reader, letter(70, "Вопрос Веры", now, days_ago=1, to=[VERA_LOGIN]), VERA_LOGIN)
    await factories.read_due()
    veras_chain = await chain_id_of(vera, "Вопрос Веры")
    veras_project = await factories.create_project(vera, RENOVATION, "Ремонт у Веры")
    await move_chain(vera, veras_chain, veras_project["id"], new_thread_name="Ветка Веры")
    veras_before = await chain_location(vera, veras_chain)
    assert veras_before["state"] == "placed"

    into_project = await move_chain_response(vera, veras_chain, renovation["id"])
    into_thread = await move_chain_response(
        vera, veras_chain, renovation["id"], thread_id=annas_thread["id"]
    )

    assert (into_project.status_code, into_thread.status_code) == (HTTPStatus.NOT_FOUND,) * 2
    assert into_project.json()["error"]["code"] == "not_found"
    assert into_thread.json()["error"]["code"] == "not_found"
    assert await chain_location(vera, veras_chain) == veras_before
    assert tree_snapshot(await open_project(anna, renovation["id"])) == annas_before
    assert [t["name"] for t in await project_threads(anna, renovation["id"])] == [ACTS_THREAD]


async def test_fr40_another_users_chain_cannot_be_opened_or_moved(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40 «Another user's chain»
    anna = await anna_with_chains(factories, reader, [ACT])
    act_id = await chain_id_of(anna, ACT)
    vera = await vera_with_mailbox(factories)
    veras_project = await factories.create_project(vera, RENOVATION, "Ремонт офиса")

    opened = await vera.get(f"{API}/placements/{act_id}")
    moved = await move_chain_response(vera, act_id, veras_project["id"])

    assert (opened.status_code, moved.status_code) == (HTTPStatus.NOT_FOUND,) * 2
    assert opened.json()["error"]["code"] == moved.json()["error"]["code"] == "not_found"
    assert (await chain_location(anna, act_id))["state"] == "none"
    assert thread_subjects(await open_project(vera, veras_project["id"])) == {}


async def test_fr40_the_threads_of_a_project_are_listed_for_the_owner_only(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-40 «Another user's project or thread»: the owner lists the threads, Вера gets «not found»
    anna = await anna_with_chains(factories, reader, [ACT, DESIGN])
    renovation = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    first = await move_chain(
        anna, await chain_id_of(anna, ACT), renovation["id"], new_thread_name=ACTS_THREAD
    )
    second = await move_chain(
        anna, await chain_id_of(anna, DESIGN), renovation["id"], new_thread_name="Дизайн"
    )
    vera = await vera_with_mailbox(factories)

    owners = await anna.get(f"{API}/projects/{renovation['id']}/threads")
    strangers = await vera.get(f"{API}/projects/{renovation['id']}/threads")

    assert owners.status_code == HTTPStatus.OK
    assert owners.json() == [first["thread"], second["thread"]]
    assert strangers.status_code == HTTPStatus.NOT_FOUND
    assert strangers.json()["error"]["code"] == "not_found"
