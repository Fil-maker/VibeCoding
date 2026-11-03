"""FR-39 through `read_due_mailboxes` and the HTTP API: placing the chains of newly read emails."""

from datetime import timedelta
from typing import Any

from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine, LocalTextEngine, PlacementEngine
from tests.factories import Factories, list_chains
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
    threads_of,
    tree_snapshot,
    use_engine,
    vera_with_mailbox,
)

FIVE_MINUTES = timedelta(minutes=5)
ESTIMATE = "Смета на ремонт офиса"


async def read_again(factories: Factories, engine: PlacementEngine) -> None:
    """Five minutes later, a reading pass that places the new chains with `engine`."""
    factories.clock.advance(FIVE_MINUTES)
    await factories.read_due(engine)


async def filled(
    factories: Factories, client: AsyncClient, name: str, description: str
) -> dict[str, Any]:
    """Create a project and fill it with the engine in use; returns its summary."""
    project = await factories.create_project(client, name, description)
    await fill_project(client, project["id"])
    return project


async def anna_with_filled_demo_projects(
    factories: Factories, reader: FakeMailReader
) -> tuple[AsyncClient, dict[str, str]]:
    """Анна with the demo mail read and the three demo projects filled by the local engine."""
    anna = await signed_in_with_mailbox(factories, DEMO_LOGINS[0])
    await factories.connect_mailbox(anna, DEMO_LOGINS[1])
    load_demo_mail(reader, factories.clock.now())
    await factories.read_due()
    use_engine(factories.app, LocalTextEngine())
    ids = {
        name: (await filled(factories, anna, name, description))["id"]
        for name, description in DEMO_PROJECTS.items()
    }
    return anna, ids


async def test_fr39_a_reply_leaves_its_chain_where_it_is(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-39 «A reply stays in its chain's place»
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    put(reader, letter(1, ESTIMATE, now, days_ago=3, text="Смета во вложении"))
    await factories.read_due()
    use_engine(factories.app, FakePlacementEngine("fake-1", {"смета": 0.5}))
    project = await filled(factories, anna, RENOVATION, "Смета на ремонт")
    [(thread_id, before)] = threads_of(await open_project(anna, project["id"])).items()
    put(reader, letter(2, "Re: " + ESTIMATE, now, days_ago=0.1, text="Смета обновлена", reply_to=1))

    await read_again(factories, FakePlacementEngine("fake-2", {"смета": 0.9}))

    [(thread_id_after, after)] = threads_of(await open_project(anna, project["id"])).items()
    assert (thread_id_after, after["name"]) == (thread_id, ESTIMATE)
    [chain] = after["chains"].values()
    [chain_before] = before["chains"].values()
    assert chain["id"] == chain_before["id"]
    assert chain["placement"] == chain_before["placement"]
    assert chain["placement"]["engine_version"] == "fake-1"
    assert chain["email_count"] == 2


async def test_fr39_a_new_chain_goes_to_its_projects_closest_thread(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-39 «A new chain finds its project»
    now = factories.clock.now()
    anna, ids = await anna_with_filled_demo_projects(factories, reader)
    subject = "Смета на покраску стен в офисе"
    text = (
        "Добрый день, Анна! Отправляю смету на покраску стен в офисе на Лесной, 12. "
        "Общая сумма около 240 000 рублей. Жду ваших замечаний."
    )
    put(
        reader,
        letter(100, subject, now, days_ago=0.1, text=text, to=[DEMO_LOGINS[0]]),
        DEMO_LOGINS[0],
    )

    await read_again(factories, LocalTextEngine())

    tree = await open_project(anna, ids[RENOVATION])
    assert subject in thread_subjects(tree)[ESTIMATE]
    [chain] = [c for c in placed_chains(tree) if c["subject"] == subject]
    placement = chain["placement"]
    assert (placement["kind"], placement["engine_version"]) == ("engine", "text-1")
    assert LocalTextEngine().sure_threshold <= placement["similarity"] <= 1


async def test_fr39_a_sure_new_chain_far_from_every_thread_starts_its_own_thread(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-39: at or above the sure threshold into the most similar project, closest thread or new one
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    put(reader, letter(1, "Смета на ремонт", now, days_ago=3))
    await factories.read_due()
    use_engine(factories.app, FakePlacementEngine("fake-1", {"ремонт": 0.5}))
    renovation = await filled(factories, anna, RENOVATION, "Ремонт офиса, переговорная")
    purchase = await filled(factories, anna, PURCHASE, "Закупка мебели")
    put(reader, letter(2, "Мебель для переговорной", now, days_ago=0.1))

    await read_again(factories, FakePlacementEngine("fake-2", {"переговорн": 0.6, "мебел": 0.4}))

    tree = await open_project(anna, renovation["id"])
    assert thread_subjects(tree) == {
        "Смета на ремонт": {"Смета на ремонт"},
        "Мебель для переговорной": {"Мебель для переговорной"},
    }
    [chain] = [c for c in placed_chains(tree) if c["subject"] == "Мебель для переговорной"]
    assert chain["placement"] == {
        "kind": "engine",
        "engine_version": "fake-2",
        "similarity": 0.6,
        "rule": None,
    }
    assert all_subjects(await open_project(anna, purchase["id"])) == set()


async def test_fr39_an_unsure_new_chain_goes_to_unassigned_of_the_most_similar_project(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-39 «An unsure new chain»
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    await factories.read_due()
    use_engine(factories.app, FakePlacementEngine("fake-1", {}))
    renovation = await filled(factories, anna, RENOVATION, "Ремонт офиса и мебель")
    purchase = await filled(factories, anna, PURCHASE, "Закупка: стулья")
    put(reader, letter(1, "Офисная мебель и стулья", now, days_ago=0.1))

    await read_again(factories, FakePlacementEngine("fake-2", {"мебель": 0.2, "стулья": 0.17}))

    tree = await open_project(anna, renovation["id"])
    assert [chain["subject"] for chain in tree["unassigned"]] == ["Офисная мебель и стулья"]
    assert placed_chains(tree) == []
    assert all_subjects(await open_project(anna, purchase["id"])) == set()


async def test_fr39_a_new_chain_below_the_lower_threshold_is_in_no_project(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-39 «A new chain of no project»
    now = factories.clock.now()
    anna, ids = await anna_with_filled_demo_projects(factories, reader)
    subject = "Скидка на абонемент в фитнес-клуб"
    text = "Только до конца месяца скидка 30% на годовой абонемент в фитнес-клуб у дома."
    put(
        reader,
        letter(
            100,
            subject,
            now,
            days_ago=0.1,
            text=text,
            sender="promo@fitness.example",
            to=[DEMO_LOGINS[0]],
        ),
        DEMO_LOGINS[0],
    )

    await read_again(factories, LocalTextEngine())

    for project_id in ids.values():
        assert subject not in all_subjects(await open_project(anna, project_id))
    assert subject in {chain["subject"] for chain in await list_chains(anna)}


async def test_fr39_two_joined_chains_keep_the_placement_made_first(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-39 «Two placed chains are joined»
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    put(reader, letter(1, ESTIMATE, now, days_ago=5, text="Смета во вложении"))
    put(reader, letter(10, "Счёт на мониторы", now, days_ago=4, sender="sales@tech.example"))
    await factories.read_due()
    engine = FakePlacementEngine("fake-1", {"смета": 0.5, "мониторы": 0.6})
    use_engine(factories.app, engine)
    renovation = await filled(factories, anna, RENOVATION, "Смета на ремонт")
    factories.clock.advance(timedelta(minutes=1))
    purchase = await filled(factories, anna, PURCHASE, "Мониторы")
    assert all_subjects(await open_project(anna, purchase["id"])) == {"Счёт на мониторы"}
    put(reader, letter(20, "Re: " + ESTIMATE, now, days_ago=0.1, reply_to=1, references=[1, 10]))

    await read_again(factories, engine)

    [chain] = placed_chains(await open_project(anna, renovation["id"]))
    assert chain["email_count"] == 3
    assert chain["placement"] == {
        "kind": "engine",
        "engine_version": "fake-1",
        "similarity": 0.5,
        "rule": None,
    }
    assert all_subjects(await open_project(anna, purchase["id"])) == set()


async def test_fr39_an_unfilled_project_gets_no_new_chain(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-39 «Unfilled projects are skipped»
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    holiday = await factories.create_project(anna, "Отпуск", "Отпуск в августе")
    put(reader, letter(1, "Отпуск в августе", now, days_ago=0.1, text="Билеты на отпуск"))

    await factories.read_due(FakePlacementEngine("fake-1", {"отпуск": 0.9}))

    tree = await open_project(anna, holiday["id"])
    assert tree["filled"] is False
    assert all_subjects(tree) == set()
    assert "Отпуск в августе" in {chain["subject"] for chain in await list_chains(anna)}


async def test_fr39_a_new_chain_of_another_user_never_goes_to_annas_project(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-39 «Only one's own projects»
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    put(reader, letter(1, ESTIMATE, now, days_ago=3))
    await factories.read_due()
    use_engine(factories.app, FakePlacementEngine("fake-1", {"ремонт": 0.5}))
    project = await filled(factories, anna, RENOVATION, "Ремонт офиса")
    before = (
        tree_snapshot(await open_project(anna, project["id"])),
        await list_projects(anna),
        await list_chains(anna),
    )
    vera = await vera_with_mailbox(factories)
    text = "Прошу согласовать ремонт офиса на Лесной"
    put(reader, letter(60, "Вопрос", now, days_ago=0.1, text=text, to=[VERA_LOGIN]), VERA_LOGIN)

    await read_again(factories, FakePlacementEngine("fake-2", {"ремонт": 0.9}))

    after = (
        tree_snapshot(await open_project(anna, project["id"])),
        await list_projects(anna),
        await list_chains(anna),
    )
    assert after == before
    assert [chain["subject"] for chain in await list_chains(vera)] == ["Вопрос"]


async def test_fr39_an_unplaced_chain_that_got_a_matching_reply_is_placed(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-39: a chain in no project that got new emails is compared with every filled project
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    put(reader, letter(1, "Письмо подрядчику", now, days_ago=3, text="Добрый день"))
    await factories.read_due()
    engine = FakePlacementEngine("fake-1", {"ремонт": 0.5})
    use_engine(factories.app, engine)
    project = await filled(factories, anna, RENOVATION, "Ремонт офиса")
    assert all_subjects(await open_project(anna, project["id"])) == set()
    put(
        reader,
        letter(2, "Re: Письмо подрядчику", now, days_ago=0.1, text="Смета на ремонт", reply_to=1),
    )

    await read_again(factories, engine)

    [chain] = placed_chains(await open_project(anna, project["id"]))
    assert (chain["subject"], chain["email_count"]) == ("Письмо подрядчику", 2)
    assert chain["placement"] == {
        "kind": "engine",
        "engine_version": "fake-1",
        "similarity": 0.5,
        "rule": None,
    }


async def test_fr39_an_unsure_chain_that_got_a_new_email_stays_in_unassigned(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-39: the engine never moves a placed chain, «Неразобранное» included
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    put(reader, letter(1, "Офисная мебель", now, days_ago=3, text="Каталог"))
    await factories.read_due()
    engine = FakePlacementEngine("fake-1", {"ремонт": 0.5, "офис": 0.2})
    use_engine(factories.app, engine)
    project = await filled(factories, anna, RENOVATION, "Ремонт офиса")
    [before] = (await open_project(anna, project["id"]))["unassigned"]
    put(
        reader,
        letter(2, "Re: Офисная мебель", now, days_ago=0.1, text="Мебель после ремонта", reply_to=1),
    )

    await read_again(factories, engine)

    tree = await open_project(anna, project["id"])
    assert placed_chains(tree) == []
    [chain] = tree["unassigned"]
    assert (chain["id"], chain["email_count"]) == (before["id"], 2)
    assert chain["placement"] == before["placement"]
    assert before["placement"]["similarity"] == 0.2
