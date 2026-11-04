"""Named queries of editing and deleting a project; every query is owner-scoped."""

from datetime import datetime
from uuid import UUID

from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects.models import ChainPlacement, PlacementKind, Project


async def lock_project_for_owner(
    session: AsyncSession, user_id: UUID, project_id: UUID
) -> Project | None:
    """Lock and return the user's project, or `None` (also for another user's project)."""
    return (
        await session.execute(
            select(Project)
            .where(Project.user_id == user_id, Project.id == project_id)
            .with_for_update()
        )
    ).scalar_one_or_none()


async def has_other_project_named_for_owner(
    session: AsyncSession, user_id: UUID, project_id: UUID, name: str
) -> bool:
    """Whether another project of the user has this name ignoring letter case."""
    found = await session.execute(
        select(Project.id).where(
            Project.user_id == user_id,
            Project.id != project_id,
            func.lower(Project.name) == name.lower(),
        )
    )
    return found.first() is not None


async def count_chains_in_project_for_owner(
    session: AsyncSession, user_id: UUID, project_id: UUID
) -> int:
    """How many of the user's chains are in the project, in threads or unassigned."""
    found = await session.execute(
        select(func.count())
        .select_from(ChainPlacement)
        .where(ChainPlacement.user_id == user_id, ChainPlacement.project_id == project_id)
    )
    return found.scalar_one()


async def exclude_placements_of_project_for_owner(
    session: AsyncSession, user_id: UUID, project_id: UUID, now: datetime
) -> None:
    """Rewrite every placement row of the project to `excluded`: taken out by hand."""
    await session.execute(
        update(ChainPlacement)
        .where(ChainPlacement.user_id == user_id, ChainPlacement.project_id == project_id)
        .values(
            kind=PlacementKind.EXCLUDED,
            project_id=None,
            thread_id=None,
            similarity=None,
            engine_version=None,
            rule_condition=None,
            rule_value=None,
            placed_at=now,
        )
    )


async def delete_project_for_owner(session: AsyncSession, project: Project) -> None:
    """Delete a project already looked up under the owner filter; threads and rules cascade."""
    await session.delete(project)
    await session.flush()
