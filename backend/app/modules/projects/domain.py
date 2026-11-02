"""Pure logic of projects: bands of similarity, thread choice and the tree of a project."""

from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID

from app.modules.correspondence.schemas import ChainFacts
from app.modules.projects.schemas import (
    CounterpartyNode,
    PlacedChain,
    Placement,
    ProjectTree,
    ThreadNode,
)
from app.platform.placement_engine import PlacementEngine

SIMILARITY_DECIMALS = 4


class Band(StrEnum):
    """Where a similarity to a project description leads."""

    THREADED = "threaded"
    UNASSIGNED = "unassigned"
    OUT = "out"


@dataclass(frozen=True)
class ThreadRef:
    """A thread of a project in the tree."""

    id: UUID
    name: str


@dataclass(frozen=True)
class PlacementEntry:
    """A stored placement as the tree reads it; a null `thread_id` is «Неразобранное»."""

    chain_id: UUID
    thread_id: UUID | None
    kind: str
    similarity: float | None
    engine_version: str | None


@dataclass(frozen=True)
class ProjectHead:
    """The project columns a tree shows."""

    id: UUID
    name: str
    description: str
    is_filled: bool


def classify(engine: PlacementEngine, similarity: float) -> Band:
    """The band of a similarity by the engine's thresholds (inclusive at the lower edge)."""
    if similarity >= engine.sure_threshold:
        return Band.THREADED
    if similarity >= engine.lower_threshold:
        return Band.UNASSIGNED
    return Band.OUT


def choose_thread(
    engine: PlacementEngine, document: str, thread_documents: Sequence[str], corpus: Sequence[str]
) -> int | None:
    """The index of the thread most like the chain, if it reaches the thread threshold.

    Ties go to the earlier thread: the strict comparison keeps the first of equal scores.
    """
    if not thread_documents:
        return None
    scores = engine.score(document, thread_documents, corpus)
    best = 0
    for index, value in enumerate(scores):
        if value > scores[best]:
            best = index
    return best if scores[best] >= engine.thread_threshold else None


def choose_best_index(scores: Sequence[float]) -> int | None:
    """The index of the highest score; ties go to the earlier one (the caller orders them)."""
    if not scores:
        return None
    best = 0
    for index, value in enumerate(scores):
        if value > scores[best]:
            best = index
    return best


def _chain_order(facts: ChainFacts) -> tuple[datetime, str, str]:
    return (facts.first_sent_at, facts.subject, facts.first_key)


def _placed_chain(entry: PlacementEntry, facts: ChainFacts) -> PlacedChain:
    return PlacedChain(
        id=facts.chain_id,
        subject=facts.subject,
        email_count=facts.email_count,
        latest_email_at=facts.latest_email_at,
        placement=Placement.model_validate(
            {
                "kind": entry.kind,
                "engine_version": entry.engine_version,
                "similarity": (
                    round(entry.similarity, SIMILARITY_DECIMALS)
                    if entry.similarity is not None
                    else None
                ),
            }
        ),
    )


def build_tree(
    head: ProjectHead,
    threads: Sequence[ThreadRef],
    placements: Sequence[PlacementEntry],
    facts: Mapping[UUID, ChainFacts],
    names: Mapping[str, str],
) -> ProjectTree:
    """The tree of a project: counterparties → threads → chains, then «Неразобранное».

    `threads` come in creation order; a chain shows under each of its counterparties, or under
    «Без контрагента» when it has none.
    """
    known = [entry for entry in placements if entry.chain_id in facts]
    in_thread: dict[UUID | None, list[PlacementEntry]] = {}
    for entry in known:
        in_thread.setdefault(entry.thread_id, []).append(entry)
    by_counterparty: dict[str | None, dict[UUID, ThreadNode]] = {}
    for thread in threads:
        entries = sorted(
            in_thread.get(thread.id, []), key=lambda e: _chain_order(facts[e.chain_id])
        )
        for entry in entries:
            chain_facts = facts[entry.chain_id]
            placed = _placed_chain(entry, chain_facts)
            owners: Sequence[str | None] = chain_facts.participants or (None,)
            for address in owners:
                nodes = by_counterparty.setdefault(address, {})
                node = nodes.setdefault(
                    thread.id, ThreadNode(id=thread.id, name=thread.name, chains=[])
                )
                node.chains.append(placed)
    counterparties = [
        CounterpartyNode(
            address=address,
            name=names.get(address, address) if address is not None else "Без контрагента",
            threads=list(nodes.values()),
        )
        for address, nodes in by_counterparty.items()
    ]
    counterparties.sort(key=lambda c: (c.address is None, c.name.lower(), c.address or ""))
    loose = sorted(
        in_thread.get(None, []),
        key=lambda e: (
            e.similarity is not None,
            -(e.similarity or 0.0),
            _chain_order(facts[e.chain_id]),
        ),
    )
    return ProjectTree(
        id=head.id,
        name=head.name,
        description=head.description,
        filled=head.is_filled,
        counterparties=counterparties,
        unassigned=[_placed_chain(entry, facts[entry.chain_id]) for entry in loose],
    )
