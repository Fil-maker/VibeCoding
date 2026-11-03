"""Named queries over the user's rules; every query is owner-scoped."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.rules.domain import RULE_LIMIT
from app.modules.rules.models import PlacementRule


def _priority_order() -> tuple[object, ...]:
    kind = case(
        (PlacementRule.condition == "address", 0),
        (PlacementRule.condition == "domain", 1),
        else_=2,
    )
    return (kind, PlacementRule.created_at, PlacementRule.id)


async def list_rules_for_owner(session: AsyncSession, user_id: UUID) -> list[PlacementRule]:
    """The user's rules in the order they win, at most `RULE_LIMIT`."""
    rows = await session.execute(
        select(PlacementRule)
        .where(PlacementRule.user_id == user_id)
        .order_by(*_priority_order())  # pyright: ignore[reportArgumentType] -- SQL expressions
        .limit(RULE_LIMIT)
    )
    return list(rows.scalars())


async def count_rules_for_owner(session: AsyncSession, user_id: UUID) -> int:
    """How many rules the user has."""
    count = await session.execute(
        select(func.count()).select_from(PlacementRule).where(PlacementRule.user_id == user_id)
    )
    return count.scalar_one()


async def get_rule_for_owner(
    session: AsyncSession, user_id: UUID, rule_id: UUID
) -> PlacementRule | None:
    """The user's rule, or `None` (also for another user's rule)."""
    return (
        await session.execute(
            select(PlacementRule).where(
                PlacementRule.user_id == user_id, PlacementRule.id == rule_id
            )
        )
    ).scalar_one_or_none()


async def has_rule_for_owner(
    session: AsyncSession,
    user_id: UUID,
    *,
    condition: str,
    value: str,
    except_rule_id: UUID | None,
) -> bool:
    """Whether the user has another rule with this condition and a value equal ignoring case."""
    query = select(PlacementRule.id).where(
        PlacementRule.user_id == user_id,
        PlacementRule.condition == condition,
        func.lower(PlacementRule.value) == value.lower(),
    )
    if except_rule_id is not None:
        query = query.where(PlacementRule.id != except_rule_id)
    return (await session.execute(query)).first() is not None


async def add_rule_for_owner(
    session: AsyncSession,
    user_id: UUID,
    *,
    condition: str,
    value: str,
    project_id: UUID,
    thread_name: str | None,
    now: datetime,
) -> PlacementRule:
    """Create a rule; the unique index refuses a repeat at flush."""
    rule = PlacementRule(
        user_id=user_id,
        condition=condition,
        value=value,
        project_id=project_id,
        thread_name=thread_name,
        created_at=now,
        updated_at=now,
    )
    session.add(rule)
    await session.flush()
    return rule


async def delete_rule_for_owner(session: AsyncSession, user_id: UUID, rule_id: UUID) -> None:
    """Delete the user's rule; placements it made keep their own copy of the rule."""
    await session.execute(
        delete(PlacementRule).where(PlacementRule.user_id == user_id, PlacementRule.id == rule_id)
    )
