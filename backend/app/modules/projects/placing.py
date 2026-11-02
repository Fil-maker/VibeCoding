"""Writing the engine's decisions: chains into threads and «Неразобранное» of one project."""

from collections.abc import Sequence
from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from app.modules.correspondence.schemas import ChainDocument
from app.modules.projects import repository
from app.modules.projects.domain import Band, choose_thread, classify
from app.platform.placement_engine import PlacementEngine


@dataclass
class ThreadState:
    """A thread of a project and the documents of the chains in it."""

    id: UUID
    position: int
    documents: list[str] = field(default_factory=lambda: [])


class Placer:
    """Places scored chains of one user, one project at a time, in the order they are given."""

    def __init__(
        self,
        session: AsyncSession,
        user_id: UUID,
        engine: PlacementEngine,
        corpus: Sequence[str],
        now: datetime,
    ) -> None:
        self._session = session
        self._user_id = user_id
        self._engine = engine
        self._corpus = corpus
        self._now = now

    async def place(
        self,
        project_id: UUID,
        threads: list[ThreadState],
        scored: Sequence[tuple[ChainDocument, float]],
    ) -> None:
        """Place each chain by its similarity to the project; `threads` grows with new threads."""
        for chain, similarity in scored:
            band = classify(self._engine, similarity)
            if band is Band.OUT:
                continue
            thread = (
                await self._thread_for(project_id, threads, chain)
                if band is Band.THREADED
                else None
            )
            await repository.add_engine_placement_for_owner(
                self._session,
                self._user_id,
                repository.NewPlacement(
                    chain_id=chain.chain_id,
                    project_id=project_id,
                    thread_id=thread.id if thread is not None else None,
                    similarity=similarity,
                    engine_version=self._engine.version,
                ),
                now=self._now,
            )

    async def _thread_for(
        self, project_id: UUID, threads: list[ThreadState], chain: ChainDocument
    ) -> ThreadState:
        joined = ["\n".join(thread.documents) for thread in threads]
        index = choose_thread(self._engine, chain.document, joined, self._corpus)
        if index is not None:
            thread = threads[index]
        else:
            position = threads[-1].position + 1 if threads else 0
            row = await repository.add_thread_for_owner(
                self._session,
                self._user_id,
                project_id=project_id,
                name=chain.subject,
                position=position,
                now=self._now,
            )
            thread = ThreadState(id=row.id, position=position)
            threads.append(thread)
        thread.documents.append(chain.document)
        return thread
