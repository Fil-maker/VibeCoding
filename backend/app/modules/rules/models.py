"""Table of the placement rules of users."""

from datetime import datetime
from uuid import UUID, uuid4

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column

from app.platform.db import Base

CONDITION_MAX_LENGTH = 16


class PlacementRule(Base):
    """A rule of a user: chains matching its condition go to a project and a thread by name."""

    __tablename__ = "placement_rules"
    __table_args__ = (
        CheckConstraint("condition in ('address', 'domain', 'subject')", name="condition"),
        Index("ix_placement_rules_user_id", "user_id"),
    )

    id: Mapped[UUID] = mapped_column(primary_key=True, default=uuid4)
    user_id: Mapped[UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    condition: Mapped[str] = mapped_column(String(CONDITION_MAX_LENGTH))
    value: Mapped[str] = mapped_column(Text)
    project_id: Mapped[UUID] = mapped_column(ForeignKey("projects.id", ondelete="CASCADE"))
    # Null means «Неразобранное».
    thread_name: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True))


Index(
    "uq_placement_rules_user_id_condition_lower_value",
    PlacementRule.user_id,
    PlacementRule.condition,
    func.lower(PlacementRule.value),
    unique=True,
)
