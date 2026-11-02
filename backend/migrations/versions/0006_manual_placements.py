"""placements by hand

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-02 10:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0006'
down_revision: str | None = '0005'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

SHAPE_CHECK = (
    "(kind = 'engine' and project_id is not null and similarity is not null"
    " and engine_version is not null)"
    " or (kind = 'manual' and project_id is not null and similarity is null"
    " and engine_version is null)"
    " or (kind = 'excluded' and project_id is null and thread_id is null"
    " and similarity is null and engine_version is null)"
)


def upgrade() -> None:
    """Apply the change."""
    op.alter_column('chain_placements', 'project_id', existing_type=sa.Uuid(), nullable=True)
    op.alter_column('chain_placements', 'similarity', existing_type=sa.Numeric(precision=5, scale=4), nullable=True)
    op.alter_column('chain_placements', 'engine_version', existing_type=sa.String(length=32), nullable=True)
    op.drop_constraint(op.f('ck_chain_placements_kind'), 'chain_placements', type_='check')
    op.create_check_constraint(op.f('ck_chain_placements_kind'), 'chain_placements', "kind in ('engine', 'manual', 'excluded')")
    op.create_check_constraint(op.f('ck_chain_placements_shape'), 'chain_placements', SHAPE_CHECK)


def downgrade() -> None:
    """Revert the change."""
    op.execute("DELETE FROM chain_placements WHERE kind IN ('manual', 'excluded')")
    op.drop_constraint(op.f('ck_chain_placements_shape'), 'chain_placements', type_='check')
    op.drop_constraint(op.f('ck_chain_placements_kind'), 'chain_placements', type_='check')
    op.create_check_constraint(op.f('ck_chain_placements_kind'), 'chain_placements', "kind in ('engine')")
    op.alter_column('chain_placements', 'engine_version', existing_type=sa.String(length=32), nullable=False)
    op.alter_column('chain_placements', 'similarity', existing_type=sa.Numeric(precision=5, scale=4), nullable=False)
    op.alter_column('chain_placements', 'project_id', existing_type=sa.Uuid(), nullable=False)
