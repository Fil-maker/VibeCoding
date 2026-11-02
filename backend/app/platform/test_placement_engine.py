"""Unit tests of the placement engine: the local text engine `text-1` and the fake one."""

import json
from email import policy
from email.message import EmailMessage
from email.parser import BytesParser
from pathlib import Path

import pytest

from app.platform.placement_engine import FakePlacementEngine, LocalTextEngine, PlacementEngine

DEMO_DIR = Path(__file__).resolve().parents[3] / "docker" / "greenmail" / "demo"

# The fixed descriptions of the demo projects and their chains (brief «Slice 1: the engine»).
DEMO_PROJECTS: dict[str, tuple[str, tuple[str, ...]]] = {
    "Ремонт офиса": (
        "Ремонт офиса на Лесной: смета, график работ, акты, дизайн переговорной",
        ("c01", "c02", "c03", "c04"),
    ),
    "Закупка техники": (
        "Закупка техники: ноутбуки, мониторы, серверы, коммерческие предложения, "
        "счета и сроки поставки",
        ("c05", "c06", "c07"),
    ),
    "Конференция ТехФорум": (
        "Участие в конференции ТехФорум: программа, доклад, стенд, бронирование зала",
        ("c08", "c09", "c10"),
    ),
}

# Background chains: they give IDF a corpus where the tested words are not everywhere.
BACKGROUND = (
    "Билеты на поезд до Казани на пятницу",
    "Отчёт за третий квартал и планы продаж",
    "Поздравляем коллег с днём рождения",
)


def has_four_decimals_at_most(value: float) -> bool:
    """Whether the float is already rounded to 4 decimals."""
    return round(value, 4) == value


# --- LocalTextEngine: identity ---


def test_local_text_engine_has_version_text_1() -> None:
    engine: PlacementEngine = LocalTextEngine()

    assert engine.version == "text-1"


def test_local_text_engine_thresholds_are_ordered_within_zero_and_one() -> None:
    engine = LocalTextEngine()

    assert 0 < engine.lower_threshold < engine.sure_threshold <= 1
    assert 0 < engine.thread_threshold <= 1


# --- LocalTextEngine: score (task 1.2) ---


def test_score_gives_one_similarity_per_document_in_their_order() -> None:
    engine = LocalTextEngine()
    documents = ["Смета на ремонт офиса", "Билеты на поезд до Казани"]
    corpus = [*documents, *BACKGROUND]

    scores = engine.score("Смета на ремонт офиса", documents, corpus)

    assert len(scores) == 2
    assert scores[0] == 1.0
    assert scores[1] < scores[0]


def test_score_is_the_same_for_the_same_inputs_on_every_call() -> None:
    engine = LocalTextEngine()
    documents = ["Смета на ремонт офиса и график работ", "Счёт на мониторы для отдела"]
    corpus = [*documents, *BACKGROUND]

    first = engine.score("ремонт офиса, смета", documents, corpus)
    second = LocalTextEngine().score("ремонт офиса, смета", documents, corpus)

    assert first == second
    assert any(score > 0 for score in first)


def test_score_does_not_depend_on_the_order_of_documents_and_corpus() -> None:
    engine = LocalTextEngine()
    documents = [
        "Смета на ремонт офиса и график работ",
        "Счёт на мониторы для отдела",
        "Программа конференции и доклад",
    ]
    corpus = [*documents, *BACKGROUND]
    query = "ремонт офиса: смета, график"

    forward = engine.score(query, documents, corpus)
    backward = engine.score(query, list(reversed(documents)), list(reversed(corpus)))

    assert dict(zip(documents, forward, strict=True)) == dict(
        zip(reversed(documents), backward, strict=True)
    )
    assert any(score > 0 for score in forward)


def test_score_lower_cases_words() -> None:
    engine = LocalTextEngine()
    documents = ["Смета на ремонт офиса"]
    corpus = [*documents, *BACKGROUND]

    (upper,) = engine.score("СМЕТА НА РЕМОНТ", documents, corpus)
    (lower,) = engine.score("смета на ремонт", documents, corpus)

    assert upper == lower
    assert upper > 0


def test_score_drops_stop_words() -> None:
    engine = LocalTextEngine()
    documents = ["Билеты на поезд"]
    corpus = [*documents, *BACKGROUND]

    (only_stop_word,) = engine.score("Встреча на складе", documents, corpus)
    (shared_word,) = engine.score("Встреча у поезда", documents, corpus)

    assert only_stop_word == 0.0
    assert shared_word > 0


def test_score_weighs_words_by_their_idf_over_the_corpus() -> None:
    engine = LocalTextEngine()
    document = "Смета на ремонт офиса"
    rare = [document, *BACKGROUND]
    common = [document, "Смета на мебель", "Смета на окна", "Смета на двери", *BACKGROUND]

    (with_rare_word,) = engine.score("смета", [document], rare)
    (with_common_word,) = engine.score("смета", [document], common)

    assert with_rare_word > 0
    assert with_common_word < with_rare_word


def test_score_matches_two_forms_of_a_russian_word_by_their_stem() -> None:
    engine = LocalTextEngine()
    documents = ["Пришлите, пожалуйста, сметы"]
    corpus = [*documents, *BACKGROUND]

    (score,) = engine.score("смета", documents, corpus)

    assert score > 0


def test_score_matches_two_forms_of_an_english_word_by_their_stem() -> None:
    engine = LocalTextEngine()
    documents = ["Please send the invoices"]
    corpus = [*documents, *BACKGROUND]

    (score,) = engine.score("invoice", documents, corpus)

    assert score > 0


def test_score_treats_yo_in_the_query_as_ye() -> None:
    engine = LocalTextEngine()
    documents = ["Выставлен счет"]
    corpus = [*documents, *BACKGROUND]

    (score,) = engine.score("счёт", documents, corpus)

    assert score > 0


def test_score_treats_yo_in_the_document_as_ye() -> None:
    engine = LocalTextEngine()
    documents = ["Выставлен счёт"]
    corpus = [*documents, *BACKGROUND]

    (score,) = engine.score("счет", documents, corpus)

    assert score > 0


def test_score_ignores_lines_quoted_with_a_greater_than_sign() -> None:
    engine = LocalTextEngine()
    plain = "Договорились о встрече"
    quoted = "\n".join([plain, "> Пришлите смету на ремонт офиса"])

    unquoted = "\n".join([plain, "Пришлите смету на ремонт офиса"])
    corpus = [plain, unquoted, *BACKGROUND]

    with_quote, without_quote, same_words_unquoted = engine.score(
        "смета на ремонт офиса", [quoted, plain, unquoted], corpus
    )

    assert with_quote == without_quote
    assert with_quote == 0.0
    assert same_words_unquoted > 0


def test_score_gives_values_between_zero_and_one_with_four_decimals_at_most() -> None:
    engine = LocalTextEngine()
    documents = [
        "Смета на ремонт офиса, график работ и акт скрытых работ",
        "Ремонт переговорной: дизайн и мебель",
        "Счёт на мониторы и сроки поставки серверов",
        "Программа конференции, доклад и стенд",
    ]
    corpus = [*documents, *BACKGROUND]

    scores = engine.score("Ремонт офиса на Лесной: смета, график работ, акты", documents, corpus)

    assert all(0.0 <= score <= 1.0 for score in scores)
    assert all(has_four_decimals_at_most(score) for score in scores)
    assert any(0.0 < score < 1.0 for score in scores)


# --- FakePlacementEngine (task 1.2) ---


def test_fake_gives_the_key_value_when_query_and_document_contain_the_key() -> None:
    engine: PlacementEngine = FakePlacementEngine("fake-1", {"смета": 0.42})

    scores = engine.score("Нужна смета", ["Вот смета на ремонт"], ["Вот смета на ремонт"])

    assert scores == [0.42]


def test_fake_matches_the_key_as_a_case_insensitive_substring() -> None:
    engine = FakePlacementEngine("fake-1", {"смета": 0.42})

    scores = engine.score("СМЕТА офиса", ["Сметами занимается Пётр"], [])

    assert scores == [0.42]


def test_fake_matches_a_key_with_capitals_in_any_case() -> None:
    engine = FakePlacementEngine("fake-1", {"ТехФорум": 0.8})

    scores = engine.score("конференция техфорум", ["Стенд на ТЕХФОРУМЕ"], [])

    assert scores == [0.8]


def test_fake_gives_zero_when_only_the_query_contains_the_key() -> None:
    engine = FakePlacementEngine("fake-1", {"смета": 0.42})

    scores = engine.score("Нужна смета", ["Билеты на поезд"], [])

    assert scores == [0.0]


def test_fake_gives_zero_when_only_the_document_contains_the_key() -> None:
    engine = FakePlacementEngine("fake-1", {"смета": 0.42})

    scores = engine.score("Билеты на поезд", ["Вот смета на ремонт"], [])

    assert scores == [0.0]


def test_fake_gives_the_highest_value_among_several_matching_keys() -> None:
    engine = FakePlacementEngine("fake-1", {"смета": 0.2, "ремонт": 0.7, "офис": 0.5})

    scores = engine.score(
        "смета ремонт офис", ["смета и ремонт офиса", "только смета", "ничего общего"], []
    )

    assert scores == [0.7, 0.2, 0.0]


def test_fake_has_the_given_version_and_default_thresholds() -> None:
    engine = FakePlacementEngine("fake-7", {})

    assert engine.version == "fake-7"
    assert engine.sure_threshold == 0.3
    assert engine.lower_threshold == 0.15
    assert engine.thread_threshold == 0.3


def test_fake_takes_the_thresholds_it_is_given() -> None:
    engine = FakePlacementEngine("fake-7", {}, sure=0.6, lower=0.2, thread=0.5)

    assert engine.sure_threshold == 0.6
    assert engine.lower_threshold == 0.2
    assert engine.thread_threshold == 0.5


# --- LocalTextEngine over the demo correspondence (task 1.3) ---


def read_email(path: Path) -> EmailMessage:
    """One demo email parsed."""
    with path.open("rb") as file:
        message = BytesParser(policy=policy.default).parse(file)
    assert isinstance(message, EmailMessage)
    return message


def email_text(message: EmailMessage) -> str:
    """The plain-text body of an email."""
    body = message.get_body(preferencelist=("plain",))
    assert isinstance(body, EmailMessage)
    content = body.get_content()
    assert isinstance(content, str)
    return content


def demo_chain_documents() -> dict[str, str]:
    """Each demo chain's document: its first subject, then its emails' text oldest first."""
    entries: list[dict[str, str]] = json.loads((DEMO_DIR / "manifest.json").read_text("utf-8"))
    files = sorted({entry["file"] for entry in entries})
    emails: dict[str, list[tuple[int, EmailMessage]]] = {}
    for name in files:
        _, chain, order = Path(name).stem.split("-")
        emails.setdefault(chain, []).append(
            (int(order.removeprefix("m")), read_email(DEMO_DIR / name))
        )
    documents: dict[str, str] = {}
    for chain, numbered in emails.items():
        ordered = [message for _, message in sorted(numbered, key=lambda pair: pair[0])]
        parts = [str(ordered[0]["Subject"]), *(email_text(message) for message in ordered)]
        documents[chain] = "\n".join(parts)
    return documents


def project_of(chain: str) -> str:
    """The demo project a chain belongs to."""
    return next(name for name, (_, chains) in DEMO_PROJECTS.items() if chain in chains)


ALL_DEMO_CHAINS = [chain for _, chains in DEMO_PROJECTS.values() for chain in chains]


def test_demo_has_the_ten_chains_of_the_brief() -> None:
    assert sorted(demo_chain_documents()) == sorted(ALL_DEMO_CHAINS)


# The distinct demo files per chain; four files are listed twice in the manifest.
DEMO_EMAIL_COUNTS = {
    "c01": 5,
    "c02": 4,
    "c03": 3,
    "c04": 3,
    "c05": 5,
    "c06": 4,
    "c07": 4,
    "c08": 5,
    "c09": 4,
    "c10": 3,
}


@pytest.mark.parametrize("chain", ALL_DEMO_CHAINS)
def test_demo_chain_document_holds_each_email_once_oldest_first(chain: str) -> None:
    document = demo_chain_documents()[chain]
    paths = sorted(
        DEMO_DIR.glob(f"*-{chain}-m*.eml"),
        key=lambda path: int(path.stem.split("-")[2].removeprefix("m")),
    )
    texts = [email_text(read_email(path)) for path in paths]

    positions = [document.index(text) for text in texts]

    assert len(texts) == DEMO_EMAIL_COUNTS[chain]
    assert all(document.count(text) == 1 for text in texts)
    assert positions == sorted(positions)


@pytest.mark.parametrize("chain", ALL_DEMO_CHAINS)
def test_demo_chain_is_sure_for_its_project_and_below_lower_for_the_others(chain: str) -> None:
    engine = LocalTextEngine()
    documents = demo_chain_documents()
    corpus = [documents[name] for name in sorted(documents)]
    own = project_of(chain)

    scores = {
        project: engine.score(description, [documents[chain]], corpus)[0]
        for project, (description, _) in DEMO_PROJECTS.items()
    }

    assert scores[own] >= engine.sure_threshold, scores
    for project, score in scores.items():
        if project != own:
            assert score < engine.lower_threshold, (project, scores)
