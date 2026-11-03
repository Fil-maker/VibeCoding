"""FR-46 through `read_due_mailboxes` and the HTTP API: placing new chains by rules."""

from datetime import timedelta

from app.platform.mail_reader import FakeMailReader
from app.platform.placement_engine import FakePlacementEngine
from tests.factories import (
    Factories,
    chain_id_of,
    chain_location,
    create_rule,
    list_chains,
    move_chain,
    project_threads,
    take_out_chain,
)
from tests.hand_placement import ACT, ESTIMATE, MANUAL, MONITORS, chain_in_tree
from tests.project_trees import (
    PETROV,
    PETROV_ADDRESS,
    PURCHASE,
    SMIRNOVA,
    VERA_LOGIN,
    all_subjects,
    fill_project,
    letter,
    open_project,
    put,
    thread_subjects,
    use_engine,
    vera_with_mailbox,
)
from tests.rule_support import (
    ADDRESS,
    DOMAIN,
    NO_ENGINE_MATCH,
    SUBJECT,
    VOLKOV,
    anna_with_two_projects,
    by_engine,
    by_rule,
    read_again,
)

PAINTING = "Смета на покраску стен"
ACT_OF_RECONCILIATION = "Акт сверки"


async def read_new(factories: Factories) -> None:
    """A reading pass that places new chains with an engine that matches nothing."""
    await read_again(factories, NO_ENGINE_MATCH)


async def test_fr46_a_rule_by_address_places_a_chain_in_a_new_thread(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46 «A rule by address»
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    await create_rule(anna, ADDRESS, PETROV_ADDRESS, renovation["id"], "Смета")
    assert await project_threads(anna, renovation["id"]) == []
    put(reader, letter(1, PAINTING, now, days_ago=1, sender=PETROV))

    await read_new(factories)

    tree = await open_project(anna, renovation["id"])
    assert thread_subjects(tree) == {"Смета": {PAINTING}}
    chain = chain_in_tree(tree, PAINTING)
    assert chain is not None
    assert chain["placement"] == by_rule(ADDRESS, PETROV_ADDRESS)


async def test_fr46_a_rule_by_domain_takes_the_domain_and_its_subdomains_only(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46 «A rule by domain»
    now = factories.clock.now()
    anna, _, purchase = await anna_with_two_projects(factories)
    await create_rule(anna, DOMAIN, "techsnab.example", purchase["id"])
    senders = {
        "Письмо от Волкова": "i.volkov@techsnab.example",
        "Заказ с поддомена": "orders@sales.techsnab.example",
        "Письмо с похожего домена": "info@mytechsnab.example",
    }
    for number, (subject, sender) in enumerate(senders.items(), start=1):
        put(reader, letter(number, subject, now, days_ago=1, sender=sender))

    await read_new(factories)

    tree = await open_project(anna, purchase["id"])
    assert thread_subjects(tree) == {}
    assert {chain["subject"] for chain in tree["unassigned"]} == {
        "Письмо от Волкова",
        "Заказ с поддомена",
    }
    assert {chain["placement"]["kind"] for chain in tree["unassigned"]} == {"rule"}
    assert {c["placement"]["rule"]["value"] for c in tree["unassigned"]} == {"techsnab.example"}
    assert "Письмо с похожего домена" not in all_subjects(tree)
    assert "Письмо с похожего домена" in {c["subject"] for c in await list_chains(anna)}


async def test_fr46_a_rule_by_subject_words_takes_a_chain_with_all_of_them(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46 «A rule by subject words»
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    await create_rule(anna, SUBJECT, "акт работ", renovation["id"], "Акты")
    put(reader, letter(1, ACT, now, days_ago=2))
    put(reader, letter(2, ACT_OF_RECONCILIATION, now, days_ago=1))

    await read_new(factories)

    tree = await open_project(anna, renovation["id"])
    assert thread_subjects(tree) == {"Акты": {ACT}}
    assert chain_in_tree(tree, ACT)["placement"] == by_rule(SUBJECT, "акт работ")  # type: ignore[index] -- chain_in_tree is Optional; a missing chain fails the test here
    assert ACT_OF_RECONCILIATION not in all_subjects(tree)


async def test_fr46_a_word_inside_another_word_does_not_match(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46 «A word inside another word»
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    await create_rule(anna, SUBJECT, "акт", renovation["id"])
    put(reader, letter(1, "Новый контакт поставщика", now, days_ago=1))

    await read_new(factories)

    assert all_subjects(await open_project(anna, renovation["id"])) == set()
    assert "Новый контакт поставщика" in {c["subject"] for c in await list_chains(anna)}


async def test_fr46_letter_case_and_yo_are_ignored(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46 «Letter case and «ё»»
    now = factories.clock.now()
    anna, _, purchase = await anna_with_two_projects(factories)
    await create_rule(anna, SUBJECT, "счёт мониторы", purchase["id"])
    put(reader, letter(1, "СЧЕТ на мониторы", now, days_ago=1))

    await read_new(factories)

    tree = await open_project(anna, purchase["id"])
    [chain] = tree["unassigned"]
    assert chain["subject"] == "СЧЕТ на мониторы"
    assert chain["placement"] == by_rule(SUBJECT, "счёт мониторы")


async def test_fr46_a_thread_of_that_name_is_reused_whatever_the_case(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46 «An existing thread of that name»
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    put(reader, letter(1, ESTIMATE, now, days_ago=3))
    await read_new(factories)
    await move_chain(
        anna, await chain_id_of(anna, ESTIMATE), renovation["id"], new_thread_name=ESTIMATE
    )
    [thread] = await project_threads(anna, renovation["id"])
    await create_rule(
        anna,
        ADDRESS,
        "o.smirnova@interior-studio.example",
        renovation["id"],
        "смета на ремонт офиса",
    )
    put(reader, letter(2, PAINTING, now, days_ago=1, sender=SMIRNOVA))

    await read_new(factories)

    assert await project_threads(anna, renovation["id"]) == [thread]
    location = await chain_location(anna, await chain_id_of(anna, PAINTING))
    assert location["thread"] == thread
    assert location["placement"]["kind"] == "rule"
    assert thread_subjects(await open_project(anna, renovation["id"])) == {
        ESTIMATE: {ESTIMATE, PAINTING}
    }


async def test_fr46_an_address_wins_over_a_domain(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46 «An address wins over a domain»
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    await create_rule(anna, DOMAIN, "stroymaster.example", renovation["id"])
    factories.clock.advance(timedelta(minutes=1))
    await create_rule(anna, ADDRESS, PETROV_ADDRESS, purchase["id"])
    put(reader, letter(1, PAINTING, now, days_ago=1, sender=PETROV))

    await read_new(factories)

    assert all_subjects(await open_project(anna, renovation["id"])) == set()
    [chain] = (await open_project(anna, purchase["id"]))["unassigned"]
    assert (chain["subject"], chain["placement"]) == (PAINTING, by_rule(ADDRESS, PETROV_ADDRESS))


async def test_fr46_of_one_kind_the_earlier_rule_wins(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46 «Of one kind the earlier wins»
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    await create_rule(anna, SUBJECT, "смета", renovation["id"])
    factories.clock.advance(timedelta(minutes=1))
    await create_rule(anna, SUBJECT, "офис", purchase["id"])
    put(reader, letter(1, ESTIMATE, now, days_ago=1))

    await read_new(factories)

    [chain] = (await open_project(anna, renovation["id"]))["unassigned"]
    assert (chain["subject"], chain["placement"]) == (ESTIMATE, by_rule(SUBJECT, "смета"))
    assert all_subjects(await open_project(anna, purchase["id"])) == set()


async def test_fr46_a_chain_placed_by_hand_is_not_taken_by_a_rule(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46 «A chain placed by hand»
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    put(reader, letter(1, ACT, now, days_ago=3))
    await read_new(factories)
    act_id = await chain_id_of(anna, ACT)
    await move_chain(anna, act_id, purchase["id"])
    await create_rule(anna, SUBJECT, "акт работ", renovation["id"])
    put(reader, letter(2, "Re: " + ACT, now, days_ago=0.1, reply_to=1))

    await read_new(factories)

    location = await chain_location(anna, act_id)
    assert location["project"] == {"id": purchase["id"], "name": PURCHASE}
    assert location["placement"] == MANUAL
    assert all_subjects(await open_project(anna, renovation["id"])) == set()


async def test_fr46_a_chain_taken_out_is_not_taken_by_a_rule(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46 «A chain taken out»
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    put(reader, letter(1, ACT_OF_RECONCILIATION, now, days_ago=3))
    await read_new(factories)
    chain_id = await chain_id_of(anna, ACT_OF_RECONCILIATION)
    await move_chain(anna, chain_id, purchase["id"])
    await take_out_chain(anna, chain_id)
    await create_rule(anna, SUBJECT, "акт", renovation["id"])
    put(reader, letter(2, "Re: " + ACT_OF_RECONCILIATION, now, days_ago=0.1, reply_to=1))

    await read_new(factories)

    assert await chain_location(anna, chain_id) == {
        "state": "excluded",
        "project": None,
        "thread": None,
        "placement": None,
    }
    assert all_subjects(await open_project(anna, renovation["id"])) == set()
    assert all_subjects(await open_project(anna, purchase["id"])) == set()


async def test_fr46_a_new_rule_moves_no_placed_chain(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46 «A new rule moves nothing»
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    put(reader, letter(1, MONITORS, now, days_ago=3, text="Мониторы для ремонта"))
    await read_new(factories)
    use_engine(factories.app, FakePlacementEngine("fake-1", {"ремонт": 0.5}))
    await fill_project(anna, renovation["id"])
    chain_id = await chain_id_of(anna, MONITORS)
    before = await chain_location(anna, chain_id)
    assert before["placement"] == by_engine("fake-1", 0.5)

    await create_rule(anna, SUBJECT, "мониторы", purchase["id"])
    await read_new(factories)

    assert await chain_location(anna, chain_id) == before
    assert all_subjects(await open_project(anna, purchase["id"])) == set()


async def test_fr46_a_rule_never_takes_a_chain_of_another_user(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46 «Only one's own chains»
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    await create_rule(anna, DOMAIN, "stroymaster.example", renovation["id"])
    vera = await vera_with_mailbox(factories)
    put(reader, letter(1, PAINTING, now, days_ago=1, to=[VERA_LOGIN]), VERA_LOGIN)

    await read_new(factories)

    assert all_subjects(await open_project(anna, renovation["id"])) == set()
    assert [chain["subject"] for chain in await list_chains(vera)] == [PAINTING]
    assert [chain["subject"] for chain in await list_chains(anna)] == []


async def test_fr46_a_rule_does_not_match_a_recipient_of_the_chain(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-46: a rule matches when an email came from the rule's address, not when it was sent to it
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    await create_rule(anna, DOMAIN, "techsnab.example", renovation["id"])
    put(reader, letter(1, "Вопрос поставщику", now, days_ago=1, to=[VOLKOV]))

    await read_new(factories)

    assert all_subjects(await open_project(anna, renovation["id"])) == set()
