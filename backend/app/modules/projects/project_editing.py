"""Use cases of editing and deleting a project; they run in the caller's transaction."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.projects import editing_repository
from app.modules.projects.errors import ProjectExists
from app.modules.projects.models import Project
from app.modules.projects.schemas import ProjectDeletion, ProjectEdit
from app.modules.rules.service import count_rules_targeting
from app.platform.errors import NotFound


async def edit_project(
    session: AsyncSession, user_id: UUID, project_id: UUID, body: ProjectEdit, now: datetime
) -> Project:
    """Change the name and description; no chain moves.

    Raises `NotFound` for another user's or an unknown project and `ProjectExists` when another
    project has the name ignoring letter case. `description_changed_at` moves only when the
    description differs.
    """
    project = await editing_repository.lock_project_for_owner(session, user_id, project_id)
    if project is None:
        raise NotFound
    if await editing_repository.has_other_project_named_for_owner(
        session, user_id, project.id, body.name
    ):
        raise ProjectExists
    if body.description != project.description:
        project.description = body.description
        project.description_changed_at = now
    project.name = body.name
    await session.flush()
    return project


async def read_deletion(session: AsyncSession, user_id: UUID, project_id: UUID) -> ProjectDeletion:
    """What deleting the project takes along; `NotFound` for another user's or an unknown id."""
    project = await editing_repository.lock_project_for_owner(session, user_id, project_id)
    if project is None:
        raise NotFound
    return ProjectDeletion(
        chain_count=await editing_repository.count_chains_in_project_for_owner(
            session, user_id, project.id
        ),
        rule_count=await count_rules_targeting(session, user_id, project.id),
    )


async def delete_project(
    session: AsyncSession, user_id: UUID, project_id: UUID, now: datetime
) -> None:
    """Take every chain of the project out by hand, then delete it with its threads and rules.

    The placements are rewritten first: the cascade would otherwise delete their rows and the
    chains would become free for the engine and the rules to place again.
    """
    project = await editing_repository.lock_project_for_owner(session, user_id, project_id)
    if project is None:
        raise NotFound
    await editing_repository.exclude_placements_of_project_for_owner(
        session, user_id, project.id, now
    )
    await editing_repository.delete_project_for_owner(session, project)
