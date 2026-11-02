"""Use cases of projects: create, list, show as a tree, fill, and place new chains."""

from collections.abc import Sequence
from datetime import datetime
from typing import Annotated
from uuid import UUID

from fastapi import Depends
from psycopg.errors import UniqueViolation
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.correspondence.schemas import ChainDocument
from app.modules.correspondence.service import (
    get_latest_sender_names,
    list_chain_documents,
    list_chain_facts,
)
from app.modules.projects import repository
from app.modules.projects.domain import (
    PlacementEntry,
    ProjectHead,
    ThreadRef,
    build_tree,
    choose_best_index,
)
from app.modules.projects.errors import ProjectExists
from app.modules.projects.models import Project
from app.modules.projects.placing import Placer, ThreadState
from app.modules.projects.schemas import ProjectCreate, ProjectSummary, ProjectTree
from app.platform.auth_context import AuthContext
from app.platform.clock import Clock
from app.platform.db import get_database_session
from app.platform.errors import NotFound
from app.platform.placement_engine import PlacementEngine


def _summary(row: repository.SummaryRow) -> ProjectSummary:
    return ProjectSummary(
        id=row.project.id,
        name=row.project.name,
        filled=row.project.filled_at is not None,
        placed_count=row.placed_count,
        unassigned_count=row.unassigned_count,
    )


async def _load_tree(session: AsyncSession, user_id: UUID, project: Project) -> ProjectTree:
    """The tree of a project; runs in the caller's transaction."""
    threads = await repository.list_threads_of_projects_for_owner(session, user_id, [project.id])
    placements = await repository.list_placements_of_projects_for_owner(
        session, user_id, [project.id]
    )
    chain_ids = [placement.chain_id for placement in placements]
    facts = await list_chain_facts(session, user_id, chain_ids)
    names = await get_latest_sender_names(session, user_id, chain_ids)
    return build_tree(
        ProjectHead(project.id, project.name, project.description, project.filled_at is not None),
        [ThreadRef(thread.id, thread.name) for thread in threads],
        [
            PlacementEntry(
                chain_id=placement.chain_id,
                thread_id=placement.thread_id,
                kind=placement.kind,
                similarity=float(placement.similarity),
                engine_version=placement.engine_version,
            )
            for placement in placements
        ],
        facts,
        names,
    )


async def carry_placement(
    session: AsyncSession, user_id: UUID, survivor_id: UUID, merged_ids: Sequence[UUID]
) -> None:
    """Merge hook: keep the earliest placement among the chains on the survivor, drop the rest.

    Runs in the caller's transaction, before the merged chains are deleted.
    """
    await repository.carry_placement_for_owner(session, user_id, survivor_id, merged_ids)


async def _thread_states(
    session: AsyncSession,
    user_id: UUID,
    project_ids: Sequence[UUID],
    documents: dict[UUID, ChainDocument],
) -> dict[UUID, list[ThreadState]]:
    """The existing threads of these projects with the documents of their chains."""
    states: dict[UUID, ThreadState] = {}
    result: dict[UUID, list[ThreadState]] = {project_id: [] for project_id in project_ids}
    threads = await repository.list_threads_of_projects_for_owner(session, user_id, project_ids)
    for thread in threads:
        states[thread.id] = ThreadState(id=thread.id, position=thread.position)
        result[thread.project_id].append(states[thread.id])
    placements = await repository.list_placements_of_projects_for_owner(
        session, user_id, project_ids
    )
    for placement in placements:
        if (
            placement.thread_id is not None
            and placement.thread_id in states
            and placement.chain_id in documents
        ):
            states[placement.thread_id].documents.append(documents[placement.chain_id].document)
    return result


async def place_new_chains(
    session: AsyncSession,
    user_id: UUID,
    chain_ids: set[UUID],
    engine: PlacementEngine,
    now: datetime,
) -> None:
    """Place the chains that are in no project into the user's filled projects.

    Runs in the caller's transaction (the mailbox batch). Only the chains in `chain_ids` that are
    in no project are scored. A chain goes to its most similar filled project (ties: created
    first, then by name) by the same bands as a fill. Placed chains are read, for the corpus and
    for the texts of the threads, but they are never re-scored or moved, so a reply never moves
    its chain.
    """
    projects = await repository.lock_projects_for_owner(session, user_id)
    filled = sorted(
        (project for project in projects if project.filled_at is not None),
        key=lambda project: (project.created_at, project.name.lower(), project.name),
    )
    if not filled or not chain_ids:
        return
    documents = await list_chain_documents(session, user_id)
    placed = await repository.list_placed_chain_ids_for_owner(session, user_id)
    candidates = [
        item for item in documents if item.chain_id in chain_ids and item.chain_id not in placed
    ]
    if not candidates:
        return
    corpus = [item.document for item in documents]
    texts = [item.document for item in candidates]
    by_project = [engine.score(project.description, texts, corpus) for project in filled]
    groups: dict[int, list[tuple[ChainDocument, float]]] = {}
    for position, item in enumerate(candidates):
        scores = [project_scores[position] for project_scores in by_project]
        best = choose_best_index(scores)
        if best is not None:
            groups.setdefault(best, []).append((item, scores[best]))
    states = await _thread_states(
        session,
        user_id,
        [filled[index].id for index in groups],
        {item.chain_id: item for item in documents},
    )
    placer = Placer(session, user_id, engine, corpus, now)
    for index, scored in groups.items():
        project_id = filled[index].id
        await placer.place(project_id, states[project_id], scored)


class ProjectsService:
    """The user-facing use cases of projects bound to one database session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def list_projects(self, context: AuthContext) -> list[ProjectSummary]:
        """The user's projects by name, at most 200."""
        async with self._session.begin():
            rows = await repository.list_project_summaries_for_owner(self._session, context.user_id)
        return [_summary(row) for row in rows]

    async def create(
        self, context: AuthContext, clock: Clock, body: ProjectCreate
    ) -> ProjectSummary:
        """Create an empty project.

        Raises `ProjectExists` when the name differs from an existing one only in letter case.
        """
        try:
            async with self._session.begin():
                if await repository.has_project_named_for_owner(
                    self._session, context.user_id, body.name
                ):
                    raise ProjectExists
                project = await repository.add_project_for_owner(
                    self._session,
                    context.user_id,
                    name=body.name,
                    description=body.description,
                    now=clock.now(),
                )
        except IntegrityError as e:
            if isinstance(e.orig, UniqueViolation):
                raise ProjectExists from e
            raise
        return _summary(repository.SummaryRow(project, 0, 0))

    async def get_tree(self, context: AuthContext, project_id: UUID) -> ProjectTree:
        """The project as a tree; `NotFound` for another user's or an unknown id."""
        async with self._session.begin():
            project = await repository.get_project_for_owner(
                self._session, context.user_id, project_id
            )
            if project is None:
                raise NotFound
            return await _load_tree(self._session, context.user_id, project)

    async def fill(
        self, context: AuthContext, project_id: UUID, engine: PlacementEngine, clock: Clock
    ) -> ProjectTree:
        """Fill the project from its description, rebuilding the engine's placements.

        Only chains that are in no other project are taken. All the user's projects are locked,
        so a fill and the mailbox reading never place the same chain twice.
        """
        now = clock.now()
        user_id = context.user_id
        async with self._session.begin():
            projects = await repository.lock_projects_for_owner(self._session, user_id)
            project = next((item for item in projects if item.id == project_id), None)
            if project is None:
                raise NotFound
            await repository.delete_engine_placements_and_threads_for_owner(
                self._session, user_id, project.id
            )
            documents = await list_chain_documents(self._session, user_id)
            placed = await repository.list_placed_chain_ids_for_owner(self._session, user_id)
            candidates = [item for item in documents if item.chain_id not in placed]
            corpus = [item.document for item in documents]
            scores = engine.score(
                project.description, [item.document for item in candidates], corpus
            )
            placer = Placer(self._session, user_id, engine, corpus, now)
            await placer.place(project.id, [], list(zip(candidates, scores, strict=True)))
            project.filled_at = now
            return await _load_tree(self._session, user_id, project)


def get_projects_service(
    session: Annotated[AsyncSession, Depends(get_database_session)],
) -> ProjectsService:
    """Dependency factory of the projects use cases."""
    return ProjectsService(session)
