"""Applying one rule now: the chains it would move, and moving the ones the user saw."""

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.correspondence.schemas import ChainDocument
from app.modules.correspondence.service import list_chain_documents, list_chain_facts
from app.modules.projects import repository
from app.modules.projects.models import ChainPlacement, PlacementKind, Thread
from app.modules.projects.rule_placing import place_by_rules
from app.modules.projects.schemas import (
    ProjectRef,
    RuleMove,
    RuleMoveSource,
    RuleMoveTarget,
    ThreadSummary,
)
from app.modules.rules.service import MatchRule, list_match_rules, pick_winning_rule

_MOVABLE_KINDS = {PlacementKind.ENGINE, PlacementKind.RULE}


@dataclass(frozen=True)
class _Move:
    document: ChainDocument
    move: RuleMove
    former_thread_id: UUID | None


def _is_in_place(row: ChainPlacement | None, rule: MatchRule, target_thread: Thread | None) -> bool:
    """Whether the chain already sits in the rule's project and thread."""
    if row is None or row.project_id != rule.project_id:
        return False
    if rule.thread_name is None:
        return row.thread_id is None
    return target_thread is not None and row.thread_id == target_thread.id


def _build_move(
    item: ChainDocument,
    row: ChainPlacement | None,
    thread: Thread | None,
    names: dict[UUID, str],
    latest_email_at: datetime,
    target: RuleMoveTarget,
) -> _Move:
    """One move: where the chain is now (from its placement row and thread) and the target."""
    source = RuleMoveSource(state="none", project=None, thread=None)
    if row is not None and row.project_id is not None:
        source = RuleMoveSource(
            state="placed",
            project=ProjectRef(id=row.project_id, name=names[row.project_id]),
            thread=ThreadSummary(id=thread.id, name=thread.name) if thread else None,
        )
    return _Move(
        document=item,
        move=RuleMove(
            chain_id=item.chain_id,
            subject=item.subject,
            latest_email_at=latest_email_at,
            current=source,
            target=target,
        ),
        former_thread_id=thread.id if thread else None,
    )


async def _compute_moves(session: AsyncSession, user_id: UUID, rule: MatchRule) -> list[_Move]:
    """The chains that `rule` wins and that are not yet in its place, newest first."""
    documents = await list_chain_documents(session, user_id)
    rules = await list_match_rules(session, user_id)
    won = [
        item
        for item in documents
        if (winner := pick_winning_rule(rules, item.senders, item.subject)) is not None
        and winner.id == rule.id
    ]
    placements = {
        row.chain_id: row for row in await repository.list_placements_for_owner(session, user_id)
    }
    candidates = [
        item
        for item in won
        if item.chain_id not in placements or placements[item.chain_id].kind in _MOVABLE_KINDS
    ]
    if not candidates:
        return []
    project_ids: set[UUID] = {rule.project_id}
    for item in candidates:
        row = placements.get(item.chain_id)
        if row is not None and row.project_id is not None:
            project_ids.add(row.project_id)
    names = await repository.list_project_names_for_owner(session, user_id, project_ids)
    threads = await repository.list_threads_of_projects_for_owner(
        session, user_id, list(project_ids)
    )
    thread_by_id = {thread.id: thread for thread in threads}
    target_thread = (
        await repository.find_thread_by_name_for_owner(
            session, user_id, rule.project_id, rule.thread_name
        )
        if rule.thread_name is not None
        else None
    )
    facts = await list_chain_facts(session, user_id, [item.chain_id for item in candidates])
    target = RuleMoveTarget(
        project=ProjectRef(id=rule.project_id, name=names[rule.project_id]),
        thread_name=rule.thread_name,
    )
    moves: list[_Move] = []
    for item in candidates:
        row = placements.get(item.chain_id)
        if _is_in_place(row, rule, target_thread):
            continue
        thread = thread_by_id.get(row.thread_id) if row is not None and row.thread_id else None
        latest = facts[item.chain_id].latest_email_at
        moves.append(_build_move(item, row, thread, names, latest, target))
    moves.sort(key=lambda m: m.move.chain_id)
    moves.sort(key=lambda m: m.move.latest_email_at, reverse=True)
    return moves


async def list_moves(session: AsyncSession, user_id: UUID, rule: MatchRule) -> list[RuleMove]:
    """The moves of the rule, without writing; runs in the caller's transaction."""
    return [item.move for item in await _compute_moves(session, user_id, rule)]


async def apply_moves(
    session: AsyncSession,
    user_id: UUID,
    rule: MatchRule,
    chain_ids: set[UUID],
    now: datetime,
) -> int:
    """Move the chains that are in `chain_ids` and still moves of the rule; return how many.

    Runs in the caller's transaction, after it locked the user's projects. Each former
    placement is dropped, the chain is placed by the rule and a thread left empty is deleted.
    """
    chosen = [
        item
        for item in await _compute_moves(session, user_id, rule)
        if item.document.chain_id in chain_ids
    ]
    for item in chosen:
        await repository.delete_placement_for_owner(session, user_id, item.document.chain_id)
    await place_by_rules(
        session, user_id, [item.document for item in chosen], [rule], now, only_project_id=None
    )
    for item in chosen:
        if item.former_thread_id is not None:
            await repository.delete_thread_if_empty_for_owner(
                session, user_id, item.former_thread_id
            )
    return len(chosen)
