"""FR-46: the pure choice of the winning rule of a chain."""

from datetime import UTC, datetime, timedelta
from itertools import permutations
from uuid import UUID, uuid4

import pytest

from app.modules.rules.domain import MatchRule, winning_rule
from app.modules.rules.schemas import RuleCondition

START = datetime(2026, 1, 1, tzinfo=UTC)
PROJECT_ID = UUID("00000000-0000-4000-8000-000000000001")
PETROV = "s.petrov@stroymaster.example"


def rule(condition: RuleCondition, value: str, *, minutes: int = 0) -> MatchRule:
    """A rule created `minutes` after the start."""
    return MatchRule(
        id=uuid4(),
        condition=condition,
        value=value,
        project_id=PROJECT_ID,
        thread_name=None,
        created_at=START + timedelta(minutes=minutes),
    )


def subject_wins(value: str, subject: str) -> bool:
    """Whether a rule by subject words `value` matches a chain with this first subject."""
    only = rule(RuleCondition.SUBJECT, value)
    return winning_rule([only], [PETROV], subject) == only


def domain_wins(sender: str) -> bool:
    """Whether the rule «Домен» «techsnab.example» matches a chain with this one sender."""
    only = rule(RuleCondition.DOMAIN, "techsnab.example")
    return winning_rule([only], [sender], "Тема") == only


def test_fr46_no_rules_win_nothing() -> None:
    assert winning_rule([], [PETROV], "Смета") is None


def test_fr46_a_rule_by_address_matches_a_sender() -> None:
    # FR-46 «A rule by address»
    address = rule(RuleCondition.ADDRESS, PETROV)
    other = rule(RuleCondition.ADDRESS, "o.smirnova@interior-studio.example")

    assert winning_rule([other, address], ["a@x.example", PETROV], "Смета") == address
    assert winning_rule([other, address], ["a@x.example"], "Смета") is None


@pytest.mark.parametrize(
    ("sender", "matches"),
    [
        ("i.volkov@techsnab.example", True),
        ("orders@sales.techsnab.example", True),
        ("info@mytechsnab.example", False),
        ("info@techsnab.example.org", False),
    ],
)
def test_fr46_a_rule_by_domain_matches_the_domain_and_its_subdomains(
    sender: str, matches: bool
) -> None:
    # FR-46 «A rule by domain»
    assert domain_wins(sender) is matches


@pytest.mark.parametrize(
    ("value", "subject", "matches"),
    [
        ("акт работ", "Акт скрытых работ", True),
        ("акт работ", "Акт сверки", False),
        ("работ акт", "Акт скрытых работ", True),
        ("акт", "Актуальные цены", True),
        ("акт", "Новый контакт поставщика", False),
        ("акт", "Re: Акт сверки", True),
    ],
)
def test_fr46_each_rule_word_must_begin_a_word_of_the_subject(
    value: str, subject: str, matches: bool
) -> None:
    # FR-46 «A rule by subject words», «A word inside another word»
    assert subject_wins(value, subject) is matches


@pytest.mark.parametrize(
    ("value", "subject"),
    [
        ("счёт мониторы", "СЧЕТ на мониторы"),
        ("СЧЕТ МОНИТОРЫ", "Счёт на мониторы"),
        ("Счёт Мониторы", "счет на МОНИТОРЫ"),
    ],
)
def test_fr46_letter_case_is_ignored_and_yo_is_ye(value: str, subject: str) -> None:
    # FR-46 «Letter case and «ё»»
    assert subject_wins(value, subject)


def test_fr46_an_address_wins_over_a_domain_and_a_domain_over_subject_words() -> None:
    # FR-46 «An address wins over a domain»
    address = rule(RuleCondition.ADDRESS, PETROV, minutes=30)
    domain = rule(RuleCondition.DOMAIN, "stroymaster.example", minutes=20)
    words = rule(RuleCondition.SUBJECT, "смета", minutes=10)

    for order in permutations([address, domain, words]):
        assert winning_rule(order, [PETROV], "Смета на стены") == address
    for order in permutations([domain, words]):
        assert winning_rule(order, [PETROV], "Смета на стены") == domain


def test_fr46_of_one_kind_the_earlier_rule_wins_whatever_the_order() -> None:
    # FR-46 «Of one kind the earlier wins»
    first = rule(RuleCondition.SUBJECT, "смета", minutes=1)
    second = rule(RuleCondition.SUBJECT, "офис", minutes=2)
    first_domain = rule(RuleCondition.DOMAIN, "stroymaster.example", minutes=1)
    second_domain = rule(RuleCondition.DOMAIN, "example", minutes=2)

    for order in permutations([first, second]):
        assert winning_rule(order, [PETROV], "Смета на ремонт офиса") == first
    for order in permutations([first_domain, second_domain]):
        assert winning_rule(order, [PETROV], "Тема") == first_domain


def test_fr46_a_later_rule_of_a_higher_kind_beats_an_earlier_rule() -> None:
    early = rule(RuleCondition.SUBJECT, "смета", minutes=1)
    late = rule(RuleCondition.DOMAIN, "stroymaster.example", minutes=99)

    assert winning_rule([early, late], [PETROV], "Смета") == late


def test_fr46_senders_are_compared_case_insensitively() -> None:
    # design «Senders of a chain»: a sender in other letter case still matches
    address = rule(RuleCondition.ADDRESS, PETROV)
    domain = rule(RuleCondition.DOMAIN, "stroymaster.example")

    assert winning_rule([address], ["S.Petrov@StroyMaster.example"], "Тема") == address
    assert winning_rule([domain], ["S.Petrov@StroyMaster.EXAMPLE"], "Тема") == domain
