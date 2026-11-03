"""FR-35, FR-36 through the HTTP API: filling a project by the engine, and filling it again."""

from http import HTTPStatus

from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine, LocalTextEngine
from tests.factories import API, Factories
from tests.project_trees import (
    DEMO_LOGINS,
    DEMO_PROJECTS,
    PURCHASE,
    RENOVATION,
    VERA_LOGIN,
    all_subjects,
    fill_project,
    letter,
    list_projects,
    load_demo_mail,
    open_project,
    placed_chains,
    put,
    signed_in_with_mailbox,
    thread_subjects,
    tree_snapshot,
    use_engine,
    vera_with_mailbox,
)

RENOVATION_CHAINS = {
    "Смета на ремонт офиса",
    "Выбор дизайна переговорной",
    "График работ и доступ в здание",
    "Акт скрытых работ",
}


async def anna_with_demo_mail(factories: Factories, reader: FakeMailReader) -> AsyncClient:
    """Анна with both demo mailboxes connected and the demo mail read."""
    anna = await signed_in_with_mailbox(factories, DEMO_LOGINS[0])
    await factories.connect_mailbox(anna, DEMO_LOGINS[1])
    load_demo_mail(reader, factories.clock.now())
    await factories.read_due()
    return anna


async def anna_with_chains(
    factories: Factories, reader: FakeMailReader, chains: list[tuple[str, str]]
) -> AsyncClient:
    """Анна with one single-email chain per (subject, text), the first one the oldest, read."""
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    for number, (subject, text) in enumerate(chains):
        put(reader, letter(number, subject, now, days_ago=20 - number, text=text))
    await factories.read_due()
    return anna


# --- FR-35 Fill a project by the engine ---


async def test_fr35_filling_takes_the_renovation_chains_of_the_demo_mail(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-35 «Filling a project»
    anna = await anna_with_demo_mail(factories, reader)
    use_engine(factories.app, LocalTextEngine())
    project = await factories.create_project(anna, RENOVATION, DEMO_PROJECTS[RENOVATION])

    tree = await fill_project(anna, project["id"])

    assert tree["filled"] is True
    assert {chain["subject"] for chain in placed_chains(tree)} == RENOVATION_CHAINS
    assert await open_project(anna, project["id"]) == tree


async def test_fr35_similar_chains_share_a_thread_named_by_the_earlier_one(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-35 «Threads of a project»
    anna = await anna_with_chains(
        factories,
        reader,
        [
            ("Смета на ремонт офиса", "Объект на Лесной"),
            ("Выбор дизайна переговорной", "Варианты для переговорной"),
            ("Акт скрытых работ", "Объект на Лесной"),
        ],
    )
    use_engine(factories.app, FakePlacementEngine("fake-1", {"лесной": 0.5, "переговорной": 0.5}))
    project = await factories.create_project(anna, RENOVATION, "Ремонт на Лесной, переговорной")

    tree = await fill_project(anna, project["id"])

    assert thread_subjects(tree) == {
        "Смета на ремонт офиса": {"Смета на ремонт офиса", "Акт скрытых работ"},
        "Выбор дизайна переговорной": {"Выбор дизайна переговорной"},
    }


async def test_fr35_an_unsure_chain_goes_to_unassigned_and_no_thread(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-35 «Unsure chains»; a chain below the lower threshold stays out, at 0.1 as at 0.0
    anna = await anna_with_chains(
        factories,
        reader,
        [
            ("Смета на ремонт", "Текст"),
            ("Офисная мебель", "Текст"),
            ("Складские ключи", "Текст"),
            ("Билеты", "Текст"),
        ],
    )
    use_engine(
        factories.app, FakePlacementEngine("fake-1", {"ремонт": 0.5, "офис": 0.2, "склад": 0.1})
    )
    project = await factories.create_project(anna, RENOVATION, "Ремонт офиса и склада")

    tree = await fill_project(anna, project["id"])

    assert [chain["subject"] for chain in tree["unassigned"]] == ["Офисная мебель"]
    assert {chain["subject"] for chain in placed_chains(tree)} == {"Смета на ремонт"}
    [summary] = await list_projects(anna)
    assert (summary["placed_count"], summary["unassigned_count"]) == (1, 1)


async def test_fr35_a_chain_at_the_sure_threshold_is_sure_and_at_the_lower_one_is_unsure(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-35: at or above the sure threshold to a thread, between lower and sure to «Неразобранное»
    anna = await anna_with_chains(
        factories, reader, [("Смета на ремонт", "Текст"), ("Офисная мебель", "Текст")]
    )
    engine = FakePlacementEngine("fake-1", {"ремонт": 0.3, "офис": 0.15}, sure=0.3, lower=0.15)
    use_engine(factories.app, engine)
    project = await factories.create_project(anna, RENOVATION, "Ремонт офиса")

    tree = await fill_project(anna, project["id"])

    assert {chain["subject"] for chain in placed_chains(tree)} == {"Смета на ремонт"}
    assert [chain["subject"] for chain in tree["unassigned"]] == ["Офисная мебель"]


async def test_fr35_a_chain_of_another_project_is_not_taken(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-35 «Chains of another project are not taken»
    anna = await anna_with_chains(factories, reader, [("Счёт на мониторы", "Счёт во вложении")])
    use_engine(factories.app, FakePlacementEngine("fake-1", {"мониторы": 0.6}))
    purchase = await factories.create_project(anna, PURCHASE, "Закупка техники: мониторы")
    await fill_project(anna, purchase["id"])
    monitors = await factories.create_project(anna, "Мониторы", "Счёт на мониторы")

    tree = await fill_project(anna, monitors["id"])

    assert all_subjects(tree) == set()
    assert all_subjects(await open_project(anna, purchase["id"])) == {"Счёт на мониторы"}


async def test_fr35_when_nothing_matches_the_project_stays_empty_and_filled(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-35 «Nothing matches»: the best chain scores above 0, but below the lower threshold
    anna = await anna_with_chains(
        factories, reader, [("Фото яхты", "Текст"), ("Смета на ремонт", "Текст")]
    )
    use_engine(factories.app, FakePlacementEngine("fake-1", {"яхт": 0.1, "ремонт": 0.5}))
    project = await factories.create_project(anna, "Яхта", "Аренда яхты на Байкале")

    tree = await fill_project(anna, project["id"])

    assert tree["filled"] is True
    assert (tree["counterparties"], tree["unassigned"]) == ([], [])
    [summary] = await list_projects(anna)
    assert (summary["filled"], summary["placed_count"], summary["unassigned_count"]) == (
        True,
        0,
        0,
    )


async def test_fr35_filling_takes_only_the_users_own_chains(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-35 «Only one's own chains»
    # «Смета на ремонт офиса» is in Анна's filled project, «Ремонт крыши» in none of hers.
    now = factories.clock.now()
    anna = await anna_with_chains(
        factories, reader, [("Смета на ремонт офиса", "Лесная, 12"), ("Ремонт крыши", "Текст")]
    )
    use_engine(factories.app, FakePlacementEngine("fake-1", {"смета": 0.5, "ремонт": 0.5}))
    estimates = await factories.create_project(anna, "Сметы", "Смета офиса")
    await fill_project(anna, estimates["id"])
    annas_before = (
        tree_snapshot(await open_project(anna, estimates["id"])),
        await list_projects(anna),
    )
    vera = await vera_with_mailbox(factories)
    put(reader, letter(50, "Ремонт дачи", now, days_ago=3, to=[VERA_LOGIN]), VERA_LOGIN)
    await factories.read_due()
    project = await factories.create_project(vera, RENOVATION, "Ремонт офиса")

    tree = await fill_project(vera, project["id"])

    assert all_subjects(tree) == {"Ремонт дачи"}
    annas_after = (
        tree_snapshot(await open_project(anna, estimates["id"])),
        await list_projects(anna),
    )
    assert annas_after == annas_before
    assert all_subjects(await open_project(anna, estimates["id"])) == {"Смета на ремонт офиса"}


async def test_fr35_filling_another_users_project_is_not_found(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-35 «Another user's project»
    anna = await anna_with_chains(factories, reader, [("Смета на ремонт офиса", "Текст")])
    use_engine(factories.app, FakePlacementEngine("fake-1", {"ремонт": 0.5}))
    project = await factories.create_project(anna, RENOVATION, "Ремонт офиса")
    vera = await vera_with_mailbox(factories)

    response = await vera.post(f"{API}/projects/{project['id']}/fill")

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["error"]["code"] == "not_found"
    tree = await open_project(anna, project["id"])
    assert tree["filled"] is False
    assert all_subjects(tree) == set()


# --- FR-36 Fill a filled project again ---


async def test_fr36_filling_again_rebuilds_the_project_and_keeps_other_projects(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-36 «Filling again»: the route drops the engine's placements and fills anew
    anna = await anna_with_chains(
        factories,
        reader,
        [("Смета на ремонт", "Текст"), ("Акт ремонт", "Текст"), ("Смета на мониторы", "Текст")],
    )
    use_engine(factories.app, FakePlacementEngine("fake-1", {"ремонт": 0.5, "мониторы": 0.6}))
    renovation = await factories.create_project(anna, RENOVATION, "Смета: ремонт")
    purchase = await factories.create_project(anna, PURCHASE, "Мониторы")
    await fill_project(anna, renovation["id"])
    await fill_project(anna, purchase["id"])
    purchase_before = tree_snapshot(await open_project(anna, purchase["id"]))
    use_engine(factories.app, FakePlacementEngine("fake-2", {"смета": 0.4}))

    tree = await fill_project(anna, renovation["id"])

    assert [(c["subject"], c["placement"]) for c in placed_chains(tree)] == [
        (
            "Смета на ремонт",
            {"kind": "engine", "engine_version": "fake-2", "similarity": 0.4, "rule": None},
        )
    ]
    assert tree["unassigned"] == []
    assert tree_snapshot(await open_project(anna, purchase["id"])) == purchase_before
