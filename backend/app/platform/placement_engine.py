"""The placement engine: how alike a text is to documents, and the thresholds of its version.

The scoring is pure computation with no I/O; the engine never sees a user id.
`LocalTextEngine` is the deterministic local engine (TF-IDF cosine over stemmed words),
used for a project description against reply chains and for a chain against a thread.
Its three thresholds belong to its version, so any change of a threshold, a stop word
or the stemmer's version is a new engine version. `FakePlacementEngine` is the test
double; `get_placement_engine` is the dependency that keeps the app's engine in `app.state`.
"""

import math
import re
from collections import Counter
from collections.abc import Mapping, Sequence
from typing import Protocol

import snowballstemmer  # pyright: ignore[reportMissingTypeStubs] - the library ships no stubs
from fastapi import Request

SCORE_DECIMALS = 4
MIN_WORD_LENGTH = 2

# Frozen with the engine version `text-1`: tuned on the demo mail in `docker/greenmail/demo/`.
TEXT_1_SURE_THRESHOLD = 0.15
TEXT_1_LOWER_THRESHOLD = 0.05
TEXT_1_THREAD_THRESHOLD = 0.15


def _word_set(text: str) -> frozenset[str]:
    return frozenset(text.split())


RUSSIAN_STOP_WORDS = _word_set(
    """
    и в во не что он на я с со как а то все она так его но да ты к у же вы за бы по только ее
    мне было вот от меня еще нет о из ему теперь когда даже ну вдруг ли если уже или ни быть был
    него до вас нибудь опять уж вам ведь там потом себя ничего ей может они тут где есть надо
    ней для мы тебя их чем была сам чтоб без будто чего раз тоже себе под будет ж тогда кто этот
    того потому этого какой совсем ним здесь этом один почти мой тем чтобы нее сейчас были куда
    зачем всех никогда можно при наконец два об другой хоть после над больше тот через эти нас
    про всего них какая много разве три эту моя впрочем хорошо свою этой перед иногда лучше чуть
    том нельзя такой им более всегда конечно всю между добрый день здравствуйте спасибо
    пожалуйста
    """
)
ENGLISH_STOP_WORDS = _word_set(
    """
    a an the and or but if of to in on at by for with from as is are was were be been it its
    this that these those i you he she we they me my your our their not no do does did have has
    had will would can could should may might so than then there here which who whom what when
    where how all any some hello hi dear thanks thank please regards re fwd
    """
)
STOP_WORDS = RUSSIAN_STOP_WORDS | ENGLISH_STOP_WORDS

_WORD = re.compile(r"[^\W_]+")
_CYRILLIC = re.compile(r"[а-я]")


class _Stemmer(Protocol):
    """The part of a Snowball stemmer used here; the library ships no type information."""

    def stemWord(self, word: str) -> str: ...


def _make_stemmer(language: str) -> _Stemmer:
    # snowballstemmer is untyped; _Stemmer is its real shape.
    return snowballstemmer.stemmer(language)  # pyright: ignore[reportUnknownVariableType, reportUnknownMemberType, reportReturnType]


_RUSSIAN = _make_stemmer("russian")
_ENGLISH = _make_stemmer("english")


def _terms(text: str) -> list[str]:
    """Stems of the words of `text` without the quoted lines and the stop words."""
    kept = "\n".join(line for line in text.splitlines() if not line.lstrip().startswith(">"))
    terms: list[str] = []
    for word in _WORD.findall(kept.lower().replace("ё", "е")):
        if word in STOP_WORDS or len(word) < MIN_WORD_LENGTH:
            continue
        if _CYRILLIC.search(word):
            terms.append(_RUSSIAN.stemWord(word))
        elif word.isascii() and not word.isdigit():
            terms.append(_ENGLISH.stemWord(word))
        else:
            terms.append(word)
    return terms


def _vector(terms: Sequence[str], idf: Mapping[str, float], default_idf: float) -> dict[str, float]:
    """The TF-IDF vector of a document."""
    return {t: n * idf.get(t, default_idf) for t, n in Counter(terms).items()}


def _cosine(left: Mapping[str, float], right: Mapping[str, float]) -> float:
    dot = sum(value * right[term] for term, value in left.items() if term in right)
    norm = math.sqrt(sum(v * v for v in left.values())) * math.sqrt(
        sum(v * v for v in right.values())
    )
    return dot / norm if norm else 0.0


class PlacementEngine(Protocol):
    """How alike a query and documents are, and the cut-offs that go with the engine version."""

    version: str
    sure_threshold: float
    lower_threshold: float
    thread_threshold: float

    def score(self, query: str, documents: Sequence[str], corpus: Sequence[str]) -> list[float]:
        """The similarity of `query` to each document, 0 to 1 with 4 decimals; IDF over `corpus`."""
        ...


class LocalTextEngine:
    """TF-IDF cosine over Snowball stems; deterministic and independent of the input order."""

    version = "text-1"
    sure_threshold = TEXT_1_SURE_THRESHOLD
    lower_threshold = TEXT_1_LOWER_THRESHOLD
    thread_threshold = TEXT_1_THREAD_THRESHOLD

    def score(self, query: str, documents: Sequence[str], corpus: Sequence[str]) -> list[float]:
        """See `PlacementEngine.score`."""
        frequency: Counter[str] = Counter()
        for text in corpus:
            frequency.update(set(_terms(text)))
        size = len(corpus)
        idf = {term: math.log((1 + size) / (1 + n)) + 1.0 for term, n in frequency.items()}
        default_idf = math.log(1 + size) + 1.0
        query_vector = _vector(_terms(query), idf, default_idf)
        return [
            round(_cosine(query_vector, _vector(_terms(d), idf, default_idf)), SCORE_DECIMALS)
            for d in documents
        ]


class FakePlacementEngine:
    """A test engine: a document scores the highest value of the keys found in both."""

    def __init__(
        self,
        version: str,
        scores: Mapping[str, float],
        sure: float = 0.3,
        lower: float = 0.15,
        thread: float = 0.3,
    ) -> None:
        self.version = version
        self.sure_threshold = sure
        self.lower_threshold = lower
        self.thread_threshold = thread
        self._scores = dict(scores)

    def score(self, query: str, documents: Sequence[str], corpus: Sequence[str]) -> list[float]:
        """See `PlacementEngine.score`; `corpus` is ignored."""
        del corpus
        lowered_query = query.lower()
        result: list[float] = []
        for document in documents:
            lowered = document.lower()
            found = [
                value
                for key, value in self._scores.items()
                if key.lower() in lowered_query and key.lower() in lowered
            ]
            result.append(round(max(found), SCORE_DECIMALS) if found else 0.0)
        return result


def get_placement_engine(request: Request) -> PlacementEngine:
    """Dependency: the app's engine, created on first use; tests override it with the fake."""
    engine: PlacementEngine | None = getattr(request.app.state, "placement_engine", None)
    if engine is None:
        engine = LocalTextEngine()
        request.app.state.placement_engine = engine
    return engine
