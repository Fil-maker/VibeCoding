"""FR-43, FR-44, FR-45 through the HTTP API: creating, listing, editing and deleting rules."""

from datetime import timedelta
from http import HTTPStatus
from typing import Any

import pytest
from httpx import AsyncClient

from app.platform.mail_reader import FakeMailReader
from tests.factories import (
    API,
    VERA_EMAIL,
    Factories,
    chain_id_of,
    chain_location,
    create_rule,
    create_rule_response,
    delete_rule,
    delete_rule_response,
    list_rules,
    update_rule,
    update_rule_response,
)
from tests.project_trees import (
    PETROV_ADDRESS,
    PURCHASE,
    RENOVATION,
    UNKNOWN_ID,
    letter,
    put,
)
from tests.rule_support import (
    ADDRESS,
    DOMAIN,
    SUBJECT,
    VOLKOV,
    anna_with_two_projects,
    by_rule,
    read_again,
)

RULE_EXISTS = "Такое правило уже есть"
TOO_MANY_RULES = "Правил не может быть больше 200"
DOMAIN_MESSAGE = "Укажите домен, например stroymaster.example"
MAX_RULES = 200


async def vera_signed_in(factories: Factories) -> AsyncClient:
    """Вера signed in, without mailboxes."""
    return await factories.signed_in(await factories.confirmed_user(email=VERA_EMAIL))


def listed(rules: list[dict[str, Any]]) -> list[tuple[str, str, str, str | None]]:
    """Condition, value, project name and thread name of each rule."""
    return [(r["condition"], r["value"], r["project"]["name"], r["thread_name"]) for r in rules]


# --- FR-43 Create a rule ---


async def test_fr43_a_rule_by_address_is_kept_lower_cased_with_its_target(
    factories: Factories,
) -> None:
    # FR-43 «A rule by address»
    anna, renovation, _ = await anna_with_two_projects(factories)

    rule = await create_rule(
        anna, ADDRESS, "S.Petrov@StroyMaster.example", renovation["id"], "Смета"
    )

    assert rule["condition"] == ADDRESS
    assert rule["value"] == PETROV_ADDRESS
    assert rule["project"] == {"id": renovation["id"], "name": RENOVATION}
    assert rule["thread_name"] == "Смета"
    assert await list_rules(anna) == [rule]


async def test_fr43_a_domain_is_kept_lower_cased(factories: Factories) -> None:
    # FR-43: an address or a domain is kept in lower case
    anna, _, purchase = await anna_with_two_projects(factories)

    rule = await create_rule(anna, DOMAIN, "TechSnab.Example", purchase["id"])

    assert rule["value"] == "techsnab.example"


@pytest.mark.parametrize("thread_name", [None, "", "   "])
async def test_fr43_no_thread_name_means_unassigned(
    factories: Factories, thread_name: str | None
) -> None:
    # FR-43 «A rule into «Неразобранное»»
    anna, _, purchase = await anna_with_two_projects(factories)

    rule = await create_rule(anna, DOMAIN, "techsnab.example", purchase["id"], thread_name)

    assert listed([rule]) == [(DOMAIN, "techsnab.example", PURCHASE, None)]
    assert listed(await list_rules(anna)) == [(DOMAIN, "techsnab.example", PURCHASE, None)]


async def test_fr43_a_body_without_thread_name_means_unassigned(factories: Factories) -> None:
    # FR-43 «A rule into «Неразобранное»»: the key may be missing altogether
    anna, _, purchase = await anna_with_two_projects(factories)

    response = await anna.post(
        f"{API}/rules",
        json={"condition": DOMAIN, "value": "techsnab.example", "project_id": purchase["id"]},
    )

    assert response.status_code == HTTPStatus.CREATED, response.text
    assert response.json()["thread_name"] is None
    assert listed(await list_rules(anna)) == [(DOMAIN, "techsnab.example", PURCHASE, None)]


async def test_fr43_spaces_at_the_ends_are_dropped(factories: Factories) -> None:
    # FR-43: spaces at the ends are dropped
    anna, renovation, _ = await anna_with_two_projects(factories)

    rule = await create_rule(anna, SUBJECT, "  акт работ ", renovation["id"], "  Акты  ")

    assert (rule["value"], rule["thread_name"]) == ("акт работ", "Акты")


@pytest.mark.parametrize(
    ("condition", "value", "thread_name", "field", "message"),
    [
        (ADDRESS, "petrov", None, "value", "Укажите адрес почты"),
        (DOMAIN, "@techsnab", None, "value", DOMAIN_MESSAGE),
        (DOMAIN, "techsnab", None, "value", DOMAIN_MESSAGE),
        (SUBJECT, "   ", None, "value", "Укажите слова темы"),
        (SUBJECT, "я" * 201, None, "value", "Слова темы — не длиннее 200 символов"),
        (
            DOMAIN,
            "techsnab.example",
            "я" * 101,
            "thread_name",
            "Название ветки — не длиннее 100 символов",
        ),
    ],
)
async def test_fr43_invalid_values_are_refused_and_no_rule_is_created(
    factories: Factories,
    condition: str,
    value: str,
    thread_name: str | None,
    field: str,
    message: str,
) -> None:
    # FR-43 «Invalid values»
    anna, renovation, _ = await anna_with_two_projects(factories)

    response = await create_rule_response(anna, condition, value, renovation["id"], thread_name)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["fields"] == {field: message}
    assert await list_rules(anna) == []


async def test_fr43_the_longest_values_are_accepted(factories: Factories) -> None:
    # FR-43: subject words up to 200 characters, a thread name up to 100
    anna, renovation, _ = await anna_with_two_projects(factories)

    words = await create_rule(anna, SUBJECT, "я" * 200, renovation["id"], "я" * 100)

    assert (len(words["value"]), len(words["thread_name"])) == (200, 100)


async def test_fr43_a_rule_without_a_project_is_refused(factories: Factories) -> None:
    # FR-43 «No project»
    anna, _, _ = await anna_with_two_projects(factories)

    response = await create_rule_response(anna, DOMAIN, "techsnab.example", None)

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    error = response.json()["error"]
    assert error["code"] == "validation_failed"
    assert error["fields"] == {"project_id": "Выберите проект"}
    assert await list_rules(anna) == []


@pytest.mark.parametrize(
    ("first", "second"),
    [
        ((DOMAIN, "techsnab.example"), (DOMAIN, "TechSnab.example")),
        ((SUBJECT, "акт работ"), (SUBJECT, "Акт Работ")),
        ((ADDRESS, PETROV_ADDRESS), (ADDRESS, "S.Petrov@Stroymaster.example")),
    ],
)
async def test_fr43_a_repeated_rule_is_refused(
    factories: Factories, first: tuple[str, str], second: tuple[str, str]
) -> None:
    # FR-43 «A repeated rule»
    anna, renovation, purchase = await anna_with_two_projects(factories)
    created = await create_rule(anna, *first, purchase["id"])

    response = await create_rule_response(anna, *second, renovation["id"])

    assert response.status_code == HTTPStatus.CONFLICT
    error = response.json()["error"]
    assert (error["code"], error["message"]) == ("rule_exists", RULE_EXISTS)
    assert await list_rules(anna) == [created]


async def test_fr43_the_same_value_under_another_condition_is_not_a_repeat(
    factories: Factories,
) -> None:
    # FR-43: a repeat has the same condition and value
    anna, renovation, _ = await anna_with_two_projects(factories)
    await create_rule(anna, SUBJECT, "techsnab.example", renovation["id"])

    response = await create_rule_response(anna, DOMAIN, "techsnab.example", renovation["id"])

    assert response.status_code == HTTPStatus.CREATED


async def test_fr43_the_201st_rule_is_refused(factories: Factories) -> None:
    # FR-43 «Too many rules»
    anna, renovation, _ = await anna_with_two_projects(factories)
    for number in range(MAX_RULES):
        await create_rule(anna, SUBJECT, f"тема{number}", renovation["id"])

    response = await create_rule_response(anna, SUBJECT, "ещё одна", renovation["id"])

    assert response.status_code == HTTPStatus.CONFLICT
    error = response.json()["error"]
    assert (error["code"], error["message"]) == ("too_many_rules", TOO_MANY_RULES)
    assert len(await list_rules(anna)) == MAX_RULES


async def test_fr43_another_users_project_is_not_found_and_no_rule_is_created(
    factories: Factories,
) -> None:
    # FR-43 «Another user's project»
    anna, renovation, _ = await anna_with_two_projects(factories)
    vera = await vera_signed_in(factories)

    response = await create_rule_response(vera, DOMAIN, "techsnab.example", renovation["id"])

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert response.json()["error"]["code"] == "not_found"
    assert await list_rules(vera) == []
    assert await list_rules(anna) == []


async def test_fr43_an_unknown_project_is_not_found(factories: Factories) -> None:
    anna, _, _ = await anna_with_two_projects(factories)

    response = await create_rule_response(anna, DOMAIN, "techsnab.example", UNKNOWN_ID)

    assert response.status_code == HTTPStatus.NOT_FOUND
    assert await list_rules(anna) == []


async def test_rule_routes_need_a_signed_in_user_and_the_right_origin(
    factories: Factories, client: AsyncClient
) -> None:
    # design «Interface»: 401 not_signed_in, 403 forbidden_origin
    anna, renovation, _ = await anna_with_two_projects(factories)
    rule = await create_rule(anna, DOMAIN, "techsnab.example", renovation["id"])
    attacker = await factories.open_client(origin="http://attacker.test")
    attacker.cookies.set("vc_session", anna.cookies["vc_session"])
    body = {"condition": DOMAIN, "value": "a.example", "project_id": renovation["id"]}

    anonymous = [
        await client.get(f"{API}/rules"),
        await client.post(f"{API}/rules", json=body),
        await client.put(f"{API}/rules/{rule['id']}", json=body),
        await client.delete(f"{API}/rules/{rule['id']}"),
    ]
    foreign = [
        await attacker.post(f"{API}/rules", json=body),
        await attacker.put(f"{API}/rules/{rule['id']}", json=body),
        await attacker.delete(f"{API}/rules/{rule['id']}"),
    ]

    assert [r.status_code for r in anonymous] == [HTTPStatus.UNAUTHORIZED] * 4
    assert {r.json()["error"]["code"] for r in anonymous} == {"not_signed_in"}
    assert [r.status_code for r in foreign] == [HTTPStatus.FORBIDDEN] * 3
    assert {r.json()["error"]["code"] for r in foreign} == {"forbidden_origin"}
    assert await list_rules(anna) == [rule]


# --- FR-44 List the rules ---


async def test_fr44_rules_are_listed_address_then_domain_then_subject_words(
    factories: Factories,
) -> None:
    # FR-44 «The order of rules»
    anna, renovation, _ = await anna_with_two_projects(factories)
    for condition, value in [
        (SUBJECT, "акт работ"),
        (DOMAIN, "stroymaster.example"),
        (ADDRESS, PETROV_ADDRESS),
    ]:
        await create_rule(anna, condition, value, renovation["id"])
        factories.clock.advance(timedelta(minutes=1))

    rules = await list_rules(anna)

    assert [rule["condition"] for rule in rules] == [ADDRESS, DOMAIN, SUBJECT]


async def test_fr44_each_kind_is_listed_by_the_time_of_creation(factories: Factories) -> None:
    # FR-44: «each kind by the time of creation»
    anna, renovation, _ = await anna_with_two_projects(factories)
    for condition, value in [
        (SUBJECT, "второе"),
        (DOMAIN, "b.example"),
        (SUBJECT, "первое"),
        (DOMAIN, "a.example"),
    ]:
        await create_rule(anna, condition, value, renovation["id"])
        factories.clock.advance(timedelta(minutes=1))

    rules = await list_rules(anna)

    assert [rule["value"] for rule in rules] == ["b.example", "a.example", "второе", "первое"]


async def test_fr44_a_user_without_rules_gets_an_empty_list(factories: Factories) -> None:
    # FR-44 «No rules»
    anna, _, _ = await anna_with_two_projects(factories)

    assert await list_rules(anna) == []


async def test_fr44_a_user_sees_only_their_own_rules(factories: Factories) -> None:
    # FR-44 «Only one's own rules»
    anna, renovation, _ = await anna_with_two_projects(factories)
    await create_rule(anna, DOMAIN, "techsnab.example", renovation["id"])
    vera = await vera_signed_in(factories)

    assert await list_rules(vera) == []
    assert len(await list_rules(anna)) == 1


# --- FR-45 Edit and delete a rule ---


async def test_fr45_editing_a_rule_changes_its_target_and_moves_no_chain(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-45 «Editing a rule»
    now = factories.clock.now()
    anna, renovation, purchase = await anna_with_two_projects(factories)
    rule = await create_rule(anna, DOMAIN, "techsnab.example", purchase["id"])
    put(reader, letter(1, "Счёт на мониторы", now, days_ago=1, sender=VOLKOV))
    await read_again(factories)
    chain_id = await chain_id_of(anna, "Счёт на мониторы")
    before = await chain_location(anna, chain_id)
    assert before["project"] == {"id": purchase["id"], "name": PURCHASE}

    changed = await update_rule(
        anna, rule["id"], DOMAIN, "techsnab.example", renovation["id"], "Поставки"
    )

    assert changed["id"] == rule["id"]
    assert listed(await list_rules(anna)) == [(DOMAIN, "techsnab.example", RENOVATION, "Поставки")]
    assert await chain_location(anna, chain_id) == before
    assert before["placement"] == by_rule(DOMAIN, "techsnab.example")


async def test_fr45_an_edit_is_checked_as_a_creation_is(factories: Factories) -> None:
    # FR-45: «by the same checks as on creation»
    anna, renovation, _ = await anna_with_two_projects(factories)
    rule = await create_rule(anna, DOMAIN, "techsnab.example", renovation["id"])

    response = await update_rule_response(anna, rule["id"], DOMAIN, "techsnab", renovation["id"])

    assert response.status_code == HTTPStatus.UNPROCESSABLE_ENTITY
    assert response.json()["error"]["fields"] == {"value": DOMAIN_MESSAGE}
    assert await list_rules(anna) == [rule]


async def test_fr45_an_edit_that_repeats_another_rule_changes_nothing(
    factories: Factories,
) -> None:
    # FR-45 «An edit that repeats another rule»
    anna, renovation, _ = await anna_with_two_projects(factories)
    await create_rule(anna, DOMAIN, "techsnab.example", renovation["id"])
    second = await create_rule(anna, DOMAIN, "stroymaster.example", renovation["id"])
    before = await list_rules(anna)

    response = await update_rule_response(
        anna, second["id"], DOMAIN, "techsnab.example", renovation["id"]
    )

    assert response.status_code == HTTPStatus.CONFLICT
    error = response.json()["error"]
    assert (error["code"], error["message"]) == ("rule_exists", RULE_EXISTS)
    assert await list_rules(anna) == before


async def test_fr45_saving_a_rule_with_its_own_value_is_not_a_repeat(
    factories: Factories,
) -> None:
    # FR-45: a rule does not repeat itself
    anna, renovation, purchase = await anna_with_two_projects(factories)
    rule = await create_rule(anna, DOMAIN, "techsnab.example", renovation["id"])

    changed = await update_rule(anna, rule["id"], DOMAIN, "TechSnab.example", purchase["id"], "Х")

    assert changed["id"] == rule["id"]
    assert listed(await list_rules(anna)) == [(DOMAIN, "techsnab.example", PURCHASE, "Х")]


async def test_fr45_deleting_a_rule_unlists_it_and_moves_no_chain(
    factories: Factories, reader: FakeMailReader
) -> None:
    # FR-45 «Deleting a rule»
    now = factories.clock.now()
    anna, renovation, _ = await anna_with_two_projects(factories)
    rule = await create_rule(anna, ADDRESS, PETROV_ADDRESS, renovation["id"])
    put(reader, letter(1, "Смета на покраску стен", now, days_ago=1))
    await read_again(factories)
    chain_id = await chain_id_of(anna, "Смета на покраску стен")
    before = await chain_location(anna, chain_id)
    assert before["placement"] == by_rule(ADDRESS, PETROV_ADDRESS)

    await delete_rule(anna, rule["id"])

    assert await list_rules(anna) == []
    assert await chain_location(anna, chain_id) == before


async def test_fr45_editing_or_deleting_another_users_rule_is_not_found(
    factories: Factories,
) -> None:
    # FR-45 «Another user's rule»
    anna, renovation, _ = await anna_with_two_projects(factories)
    annas = await create_rule(anna, DOMAIN, "techsnab.example", renovation["id"])
    vera = await vera_signed_in(factories)
    veras_project = await factories.create_project(vera, "Отпуск", "Отпуск в августе")
    veras = await create_rule(vera, SUBJECT, "отпуск", veras_project["id"])

    responses = [
        await update_rule_response(vera, annas["id"], DOMAIN, "a.example", veras_project["id"]),
        await delete_rule_response(vera, annas["id"]),
        await update_rule_response(vera, veras["id"], SUBJECT, "отпуск", renovation["id"]),
    ]

    assert [r.status_code for r in responses] == [HTTPStatus.NOT_FOUND] * 3
    assert {r.json()["error"]["code"] for r in responses} == {"not_found"}
    assert await list_rules(anna) == [annas]
    assert await list_rules(vera) == [veras]


async def test_fr45_an_unknown_rule_is_not_found(factories: Factories) -> None:
    anna, renovation, _ = await anna_with_two_projects(factories)

    responses = [
        await update_rule_response(anna, UNKNOWN_ID, DOMAIN, "a.example", renovation["id"]),
        await delete_rule_response(anna, UNKNOWN_ID),
    ]

    assert [r.status_code for r in responses] == [HTTPStatus.NOT_FOUND] * 2
