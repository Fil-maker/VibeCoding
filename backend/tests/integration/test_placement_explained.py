"""FR-37, FR-38 through the HTTP API: every placement explained, and reproducible."""

from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine, LocalTextEngine
from tests.factories import VERA_EMAIL, Factories
from tests.project_trees import (
    DEMO_LOGINS,
    DEMO_PROJECTS,
    RENOVATION,
    fill_project,
    letter,
    load_demo_mail,
    open_project,
    placed_chains,
    put,
    signed_in_with_mailbox,
    tree_snapshot,
    use_engine,
)

ESTIMATE = "Смета на ремонт офиса"


async def anna_with_estimate_and_furniture(
    factories: Factories, reader: FakeMailReader
) -> AsyncClient:
    """Анна with the chains «Смета на ремонт офиса» and «Офисная мебель», read."""
    now = factories.clock.now()
    anna = await signed_in_with_mailbox(factories)
    put(reader, letter(1, ESTIMATE, now, days_ago=5, text="Смета во вложении"))
    put(reader, letter(2, "Офисная мебель", now, days_ago=4, text="Каталог мебели"))
    await factories.read_due()
    return anna


async def demo_user(
    factories: Factories, reader: FakeMailReader, *, prefix: str, newest_first: bool
) -> AsyncClient:
    """A user whose two mailboxes `<prefix>@demo.test`, `<prefix>.work@demo.test` hold the demo
    mail, read; Анна for the prefix «anna», else Вера."""
    logins = {DEMO_LOGINS[0]: f"{prefix}@demo.test", DEMO_LOGINS[1]: f"{prefix}.work@demo.test"}
    email = None if prefix == "anna" else VERA_EMAIL
    client = await signed_in_with_mailbox(factories, logins[DEMO_LOGINS[0]], email=email)
    await factories.connect_mailbox(client, logins[DEMO_LOGINS[1]])
    load_demo_mail(reader, factories.clock.now(), logins=logins, newest_first=newest_first)
    await factories.read_due()
    return client


# --- FR-37 Explain every placement ---


async def test_fr37_a_chain_placed_by_the_engine_shows_its_version_and_similarity(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-37 «A chain placed by the engine»
    anna = await anna_with_estimate_and_furniture(factories, reader)
    use_engine(factories.app, FakePlacementEngine("text-1", {"смета": 0.4271}))
    project = await factories.create_project(anna, RENOVATION, "Смета на ремонт")

    await fill_project(anna, project["id"])

    tree = await open_project(anna, project["id"])
    [chain] = placed_chains(tree)
    assert chain["subject"] == ESTIMATE
    assert chain["placement"] == {
        "kind": "engine",
        "engine_version": "text-1",
        "similarity": 0.4271,
        "rule": None,
    }


async def test_fr37_an_unsure_chain_shows_its_version_and_similarity(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-37 «An unsure chain»
    anna = await anna_with_estimate_and_furniture(factories, reader)
    use_engine(factories.app, FakePlacementEngine("text-1", {"мебел": 0.1950}))
    project = await factories.create_project(anna, RENOVATION, "Ремонт и мебель")

    await fill_project(anna, project["id"])

    tree = await open_project(anna, project["id"])
    [chain] = tree["unassigned"]
    assert chain["subject"] == "Офисная мебель"
    assert chain["placement"] == {
        "kind": "engine",
        "engine_version": "text-1",
        "similarity": 0.195,
        "rule": None,
    }


# --- FR-38 Reproducible placement ---


async def test_fr38_filling_twice_gives_the_same_tree(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-38 «Filling twice gives the same tree»
    anna = await demo_user(factories, reader, prefix="anna", newest_first=False)
    use_engine(factories.app, LocalTextEngine())
    project = await factories.create_project(anna, RENOVATION, DEMO_PROJECTS[RENOVATION])
    first = tree_snapshot(await fill_project(anna, project["id"]))

    second = tree_snapshot(await fill_project(anna, project["id"]))

    assert first == second
    assert first[0] != ()


async def test_fr38_another_reading_order_gives_the_same_tree(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-38 «Another reading order»
    anna = await demo_user(factories, reader, prefix="anna", newest_first=False)
    vera = await demo_user(factories, reader, prefix="vera", newest_first=True)
    use_engine(factories.app, LocalTextEngine())
    annas = await factories.create_project(anna, RENOVATION, DEMO_PROJECTS[RENOVATION])
    veras = await factories.create_project(vera, RENOVATION, DEMO_PROJECTS[RENOVATION])

    annas_tree = tree_snapshot(await fill_project(anna, annas["id"]))
    veras_tree = tree_snapshot(await fill_project(vera, veras["id"]))

    assert annas_tree == veras_tree
    assert annas_tree[0] != ()


async def test_fr38_a_new_engine_version_shows_only_after_filling_again(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-38 «Another engine version»; FR-37: the similarity as computed when the chain was placed
    anna = await anna_with_estimate_and_furniture(factories, reader)
    use_engine(factories.app, FakePlacementEngine("text-1", {"смета": 0.5, "мебел": 0.2}))
    project = await factories.create_project(anna, RENOVATION, "Смета на ремонт и мебель")
    await fill_project(anna, project["id"])
    use_engine(factories.app, FakePlacementEngine("text-2", {"смета": 0.6, "мебел": 0.25}))

    before = tree_snapshot(await open_project(anna, project["id"]))
    after = tree_snapshot(await fill_project(anna, project["id"]))

    assert before == (
        ((ESTIMATE, ((ESTIMATE, "text-1", 0.5),)),),
        (("Офисная мебель", "text-1", 0.2),),
    )
    assert after == (
        ((ESTIMATE, ((ESTIMATE, "text-2", 0.6),)),),
        (("Офисная мебель", "text-2", 0.25),),
    )
