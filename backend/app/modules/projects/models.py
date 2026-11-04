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
CONDITION_MAX_LENGTH = 16
SIMILARITY_PRECISION = 5
SIMILARITY_SCALE = 4


SHAPE_CHECK = (
    "(kind = 'engine' and project_id is not null and similarity is not null"
    " and engine_version is not null)"
    " or (kind = 'manual' and project_id is not null and similarity is null"
    " and engine_version is null)"
    " or (kind = 'excluded' and project_id is null and thread_id is null"
    " and similarity is null and engine_version is null)"
    " or (kind = 'rule' and project_id is not null and similarity is null"
    " and engine_version is null)"
)
# The rule columns are set exactly for a placement by a rule.
RULE_COLUMNS_CHECK = (
    "(kind = 'rule' and rule_condition is not null and rule_value is not null)"
    " or (kind <> 'rule' and rule_condition is null and rule_value is null)"
)


class PlacementKind(StrEnum):
    """Who placed a chain."""

    ENGINE = "engine"
    MANUAL = "manual"
    EXCLUDED = "excluded"
    RULE = "rule"


class Project(Base):
    """A project of a user: a name and a description the engine matches correspondence against."""

    __tablename__ = "projects"

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    name: Mapped[str] = mapped_column(String(NAME_MAX_LENGTH))
    description: Mapped[str] = mapped_column(Text)
    filled_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    # When an edit last changed the description; after `filled_at` the project is stale.
    description_changed_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


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
        CheckConstraint("kind in ('engine', 'manual', 'excluded', 'rule')", name="kind"),
        CheckConstraint(f"({SHAPE_CHECK}) and ({RULE_COLUMNS_CHECK})", name="shape"),
        Index("ix_chain_placements_user_id_project_id", "user_id", "project_id"),
    )

    chain_id: Mapped[UUID] = mapped_column(
        ForeignKey("reply_chains.id", ondelete="CASCADE"), primary_key=True
    )
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    # Null only for an `excluded` row: the chain was taken out of projects by hand.
    project_id: Mapped[UUID | None] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    # Null means «Неразобранное»: the chain is in the project but in no thread.
    thread_id: Mapped[UUID | None] = mapped_column(ForeignKey("threads.id", ondelete="CASCADE"))
    kind: Mapped[str] = mapped_column(String(KIND_MAX_LENGTH))
    # Set exactly for an `engine` row: null for `manual`, `excluded` and `rule`.
    similarity: Mapped[Decimal | None] = mapped_column(
        Numeric(SIMILARITY_PRECISION, SIMILARITY_SCALE)
    )
    engine_version: Mapped[str | None] = mapped_column(String(ENGINE_VERSION_MAX_LENGTH))
    # The rule as it was when it placed the chain (set exactly for `rule`); later edits of the
    # rule never rewrite them.
    rule_condition: Mapped[str | None] = mapped_column(String(CONDITION_MAX_LENGTH))
    rule_value: Mapped[str | None] = mapped_column(Text)
    placed_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
