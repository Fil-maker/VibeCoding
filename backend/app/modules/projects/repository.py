"""Named queries over projects, threads and placements; every query is owner-scoped."""

from collections.abc import Sequence
from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from uuid import UUID

from sqlalchemy import delete, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.models import ChainPlacement, PlacementKind, Project, Thread

PROJECT_LIST_LIMIT = 200


@dataclass(frozen=True)
class SummaryRow:
    """A project with the counts of its chains."""

    project: Project
    placed_count: int
    unassigned_count: int


async def lock_projects_for_owner(session: AsyncSession, user_id: UUID) -> list[Project]:
    """Lock all the user's projects (in id order, so two lockers cannot deadlock) and return them.

    Holding these locks keeps a fill and a mailbox read from placing the same chain twice.
    """
    rows = await session.execute(
        select(Project).where(Project.user_id == user_id).order_by(Project.id).with_for_update()
    )
    return list(rows.scalars())


async def get_project_for_owner(
    session: AsyncSession, user_id: UUID, project_id: UUID
) -> Project | None:
    """The user's project, or `None` (also for another user's project)."""
    return (
        await session.execute(
            select(Project).where(Project.user_id == user_id, Project.id == project_id)
        )
    ).scalar_one_or_none()


async def has_project_named_for_owner(session: AsyncSession, user_id: UUID, name: str) -> bool:
    """Whether the user has a project whose name equals this one ignoring letter case."""
    found = await session.execute(
        select(Project.id).where(
            Project.user_id == user_id, func.lower(Project.name) == name.lower()
        )
    )
    return found.first() is not None


async def add_project_for_owner(
    session: AsyncSession, user_id: UUID, *, name: str, description: str, now: datetime
) -> Project:
    """Create an unfilled project."""
    project = Project(
        user_id=user_id, name=name, description=description, filled_at=None, created_at=now
    )
    session.add(project)
    await session.flush()
    return project


async def list_project_summaries_for_owner(
    session: AsyncSession, user_id: UUID
) -> list[SummaryRow]:
    """The user's projects by name with the counts of chains in threads and unassigned."""
    in_thread = func.count(ChainPlacement.chain_id).filter(ChainPlacement.thread_id.is_not(None))
    unassigned = func.count(ChainPlacement.chain_id).filter(ChainPlacement.thread_id.is_(None))
    rows = await session.execute(
        select(Project, in_thread, unassigned)
        .outerjoin(
            ChainPlacement,
            (ChainPlacement.project_id == Project.id) & (ChainPlacement.user_id == user_id),
        )
        .where(Project.user_id == user_id)
        .group_by(Project.id)
        .order_by(func.lower(Project.name), Project.name)
        .limit(PROJECT_LIST_LIMIT)
    )
    return [SummaryRow(project, placed, loose) for project, placed, loose in rows]


async def delete_engine_placements_and_threads_for_owner(
    session: AsyncSession, user_id: UUID, project_id: UUID
) -> None:
    """Drop the engine's placements of the project, then its threads."""
    await session.execute(
        delete(ChainPlacement).where(
            ChainPlacement.user_id == user_id,
            ChainPlacement.project_id == project_id,
            ChainPlacement.kind == PlacementKind.ENGINE,
        )
    )
    await session.execute(
        delete(Thread).where(Thread.user_id == user_id, Thread.project_id == project_id)
    )


async def list_placed_chain_ids_for_owner(session: AsyncSession, user_id: UUID) -> set[UUID]:
    """The user's chains that are in some project."""
    rows = await session.execute(
        select(ChainPlacement.chain_id).where(ChainPlacement.user_id == user_id)
    )
    return set(rows.scalars())


async def add_thread_for_owner(
    session: AsyncSession,
    user_id: UUID,
    *,
    project_id: UUID,
    name: str,
    position: int,
    now: datetime,
) -> Thread:
    """Create a thread of a project."""
    thread = Thread(
        user_id=user_id, project_id=project_id, name=name, position=position, created_at=now
    )
    session.add(thread)
    await session.flush()
    return thread


@dataclass(frozen=True)
class NewPlacement:
    """An engine placement to store; a null `thread_id` is «Неразобранное»."""

    chain_id: UUID
    project_id: UUID
    thread_id: UUID | None
    similarity: float
    engine_version: str


async def add_engine_placement_for_owner(
    session: AsyncSession, user_id: UUID, placement: NewPlacement, *, now: datetime
) -> None:
    """Place a chain."""
    session.add(
        ChainPlacement(
            chain_id=placement.chain_id,
            user_id=user_id,
            project_id=placement.project_id,
            thread_id=placement.thread_id,
            kind=PlacementKind.ENGINE,
            similarity=Decimal(str(placement.similarity)),
            engine_version=placement.engine_version,
            placed_at=now,
        )
    )
    await session.flush()


async def list_threads_of_projects_for_owner(
    session: AsyncSession, user_id: UUID, project_ids: Sequence[UUID]
) -> list[Thread]:
    """The threads of these projects, each project's threads in creation order."""
    rows = await session.execute(
        select(Thread)
        .where(Thread.user_id == user_id, Thread.project_id.in_(project_ids))
        .order_by(Thread.project_id, Thread.position)
    )
    return list(rows.scalars())


async def list_placements_of_projects_for_owner(
    session: AsyncSession, user_id: UUID, project_ids: Sequence[UUID]
) -> list[ChainPlacement]:
    """The placements in these projects (the reader sorts them)."""
    rows = await session.execute(
        select(ChainPlacement).where(
            ChainPlacement.user_id == user_id, ChainPlacement.project_id.in_(project_ids)
        )
    )
    return list(rows.scalars())


async def carry_placement_for_owner(
    session: AsyncSession, user_id: UUID, survivor_id: UUID, merged_ids: Sequence[UUID]
) -> None:
    """Keep on the survivor the earliest placement among it and the merged chains, drop the rest.

    Ties go to the project created first, then by name, then to the thread created first.
    """
    chain_ids = [survivor_id, *merged_ids]
    kept = (
        await session.execute(
            select(ChainPlacement.chain_id)
            .join(Project, Project.id == ChainPlacement.project_id)
            .outerjoin(Thread, Thread.id == ChainPlacement.thread_id)
            .where(ChainPlacement.user_id == user_id, ChainPlacement.chain_id.in_(chain_ids))
            .order_by(
                ChainPlacement.placed_at,
                Project.created_at,
                func.lower(Project.name),
                Thread.position.asc().nulls_last(),
            )
            .limit(1)
        )
    ).scalar_one_or_none()
    if kept is None:
        return
    await session.execute(
        delete(ChainPlacement).where(
            ChainPlacement.user_id == user_id,
            ChainPlacement.chain_id.in_(chain_ids),
            ChainPlacement.chain_id != kept,
        )
    )
    if kept != survivor_id:
        await session.execute(
            update(ChainPlacement)
            .where(ChainPlacement.user_id == user_id, ChainPlacement.chain_id == kept)
            .values(chain_id=survivor_id)
        )
