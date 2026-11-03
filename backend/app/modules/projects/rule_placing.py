"""Placing chains by the user's rules: the rule decides before the engine is asked."""

from collections.abc import Sequence
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.correspondence.schemas import ChainDocument
from app.modules.projects import repository
from app.modules.rules.service import MatchRule, pick_winning_rule


async def _thread_id_for(
    session: AsyncSession, user_id: UUID, rule: MatchRule, now: datetime
) -> UUID | None:
    """The rule's thread in its project, found by name or created; null for «Неразобранное»."""
    if rule.thread_name is None:
        return None
    found = await repository.find_thread_by_name_for_owner(
        session, user_id, rule.project_id, rule.thread_name
    )
    if found is not None:
        return found.id
    position = await repository.get_next_thread_position_for_owner(
        session, user_id, rule.project_id
    )
    created = await repository.add_thread_for_owner(
        session,
        user_id,
        project_id=rule.project_id,
        name=rule.thread_name,
        position=position,
        now=now,
    )
    return created.id


async def place_by_rules(
    session: AsyncSession,
    user_id: UUID,
    candidates: Sequence[ChainDocument],
    rules: Sequence[MatchRule],
    now: datetime,
    *,
    only_project_id: UUID | None,
) -> list[ChainDocument]:
    """Place the candidates (in reading order) by their winning rules; return the engine's share.

    With `only_project_id` (a fill) a chain whose winning rule targets another project is left
    out of the result and of every project; without it (new chains) every winning rule places.
    """
    # The rules come from the user's own rows, so a placement never crosses an owner.
    rest: list[ChainDocument] = []
    for chain in candidates:
        rule = pick_winning_rule(rules, chain.senders, chain.subject)
        if rule is None:
            rest.append(chain)
            continue
        if only_project_id is not None and rule.project_id != only_project_id:
            continue
        thread_id = await _thread_id_for(session, user_id, rule, now)
        await repository.add_rule_placement_for_owner(
            session,
            user_id,
            repository.NewRulePlacement(
                chain_id=chain.chain_id,
                project_id=rule.project_id,
                thread_id=thread_id,
                rule_condition=rule.condition.value,
                rule_value=rule.value,
            ),
            now=now,
        )
    return rest
