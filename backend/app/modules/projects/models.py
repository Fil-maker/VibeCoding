"""Tables of projects, their threads and the placements of reply chains."""

from datetime import datetime
from decimal import Decimal
from enum import StrEnum
from uuid import UUID, uuid4

from sqlalchemy import (
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base

NAME_MAX_LENGTH = 100
KIND_MAX_LENGTH = 16
ENGINE_VERSION_MAX_LENGTH = 32
SIMILARITY_PRECISION = 5
SIMILARITY_SCALE = 4


class PlacementKind(StrEnum):
    """Who placed a chain; task 1.4 adds «by hand» and «by a rule»."""

    ENGINE = "engine"


class Project(Base):
    """A project of a user: a name and a description the engine matches correspondence against."""

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    description: Mapped[str] = mapped_column(Text)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


Index("uq_projects_user_id_lower_name", Project.user_id, func.lower(Project.name), unique=True)


class Thread(Base):
    """A group of similar reply chains inside a project."""

    __tablename__ = "threads"
    __table_args__ = (UniqueConstraint("project_id", "position"),)

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(Text)
    position: Mapped[int] = mapped_column(Integer)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


class ChainPlacement(Base):
    """Where a reply chain sits: one row per chain, so a chain is in at most one project."""

    __tablename__ = "chain_placements"
    __table_args__ = (
        CheckConstraint("kind in ('engine')", name="kind"),
        Index("ix_chain_placements_user_id_project_id", "user_id", "project_id"),
    )

    chain_id: Mapped[UUID] = mapped_column(
        ForeignKey("reply_chains.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    # Null means «Неразобранное»: the chain is in the project but in no thread.
    thread_id: Mapped[UUID | None] = mapped_column(ForeignKey("threads.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(KIND_MAX_LENGTH))
    similarity: Mapped[Decimal] = mapped_column(Numeric(SIMILARITY_PRECISION, SIMILARITY_SCALE))
    engine_version: Mapped[str] = mapped_column(String(ENGINE_VERSION_MAX_LENGTH))
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
