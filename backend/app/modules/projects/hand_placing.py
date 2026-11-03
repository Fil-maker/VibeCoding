"""Placements by hand: where a chain is, moving it, and taking it out of projects."""

from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.correspondence.service import has_chain
from app.modules.projects import repository
from app.modules.projects.domain import PlacementEntry, build_placement
from app.modules.projects.errors import ChainNotInProject
from app.modules.projects.models import Project
from app.modules.projects.schemas import (
    ChainLocation,
    PlacementMove,
    ProjectRef,
    ThreadSummary,
)
from app.platform.errors import NotFound


async def _require_chain(session: AsyncSession, user_id: UUID, chain_id: UUID) -> None:
    if not await has_chain(session, user_id, chain_id):
        raise NotFound


async def _location(session: AsyncSession, user_id: UUID, chain_id: UUID) -> ChainLocation:
    row = await repository.get_placement_for_owner(session, user_id, chain_id)
    if row is None:
        return ChainLocation(state="none", project=None, thread=None, placement=None)
    if row.project_id is None:
        return ChainLocation(state="excluded", project=None, thread=None, placement=None)
    project = await repository.get_project_for_owner(session, user_id, row.project_id)
    if project is None:
        raise NotFound
    thread = None
    if row.thread_id is not None:
        found = await repository.get_thread_for_owner(session, user_id, row.thread_id)
        if found is None:
            raise NotFound
        thread = ThreadSummary(id=found.id, name=found.name)
    placement = build_placement(
        PlacementEntry(
            chain_id=row.chain_id,
            thread_id=row.thread_id,
            kind=row.kind,
            similarity=float(row.similarity) if row.similarity is not None else None,
            engine_version=row.engine_version,
            rule_condition=row.rule_condition,
            rule_value=row.rule_value,
        )
    )
    return ChainLocation(
        state="placed",
        project=ProjectRef(id=project.id, name=project.name),
        thread=thread,
        placement=placement,
    )


async def read_location(session: AsyncSession, user_id: UUID, chain_id: UUID) -> ChainLocation:
    """Where the user's chain is; `NotFound` for another user's or an unknown chain."""
    await _require_chain(session, user_id, chain_id)
    return await _location(session, user_id, chain_id)


async def _target_thread_id(
    session: AsyncSession,
    user_id: UUID,
    project: Project,
    body: PlacementMove,
    now: datetime,
) -> UUID | None:
    if body.thread_id is not None:
        thread = await repository.get_thread_for_owner(session, user_id, body.thread_id)
        if thread is None or thread.project_id != project.id:
            raise NotFound
        return thread.id
    if body.new_thread_name is not None:
        position = await repository.get_next_thread_position_for_owner(session, user_id, project.id)
        created = await repository.add_thread_for_owner(
            session,
            user_id,
            project_id=project.id,
            name=body.new_thread_name,
            position=position,
            now=now,
        )
        return created.id
    return None


async def move_chain(
    session: AsyncSession, user_id: UUID, chain_id: UUID, body: PlacementMove, now: datetime
) -> ChainLocation:
    """Place the chain by hand in a project; runs in the caller's transaction.

    Raises `NotFound` for a chain, project or thread that is not the user's, or a thread of
    another project. A thread the chain leaves is deleted when no placement points to it.
    """
    projects = await repository.lock_projects_for_owner(session, user_id)
    project = next((item for item in projects if item.id == body.project_id), None)
    if project is None:
        raise NotFound
    await _require_chain(session, user_id, chain_id)
    target = await _target_thread_id(session, user_id, project, body, now)
    old = await repository.get_placement_for_owner(session, user_id, chain_id)
    left = old.thread_id if old is not None else None
    await repository.set_manual_placement_for_owner(
        session, user_id, chain_id=chain_id, project_id=project.id, thread_id=target, now=now
    )
    if left is not None:
        await repository.delete_thread_if_empty_for_owner(session, user_id, left)
    return await _location(session, user_id, chain_id)


async def take_chain_out(
    session: AsyncSession, user_id: UUID, chain_id: UUID, now: datetime
) -> ChainLocation:
    """Take the chain out of its project for good; runs in the caller's transaction.

    Raises `ChainNotInProject` when it is already out or in no project.
    """
    await repository.lock_projects_for_owner(session, user_id)
    await _require_chain(session, user_id, chain_id)
    old = await repository.get_placement_for_owner(session, user_id, chain_id)
    if old is None or old.project_id is None:
        raise ChainNotInProject
    left = old.thread_id
    await repository.set_manual_placement_for_owner(
        session, user_id, chain_id=chain_id, project_id=None, thread_id=None, now=now
    )
    if left is not None:
        await repository.delete_thread_if_empty_for_owner(session, user_id, left)
    return await _location(session, user_id, chain_id)
