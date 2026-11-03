"""placement rules

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-02 14:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0007'
down_revision: str | None = '0006'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

OLD_SHAPE_CHECK = (
    "(kind = 'engine' and project_id is not null and similarity is not null"
    " and engine_version is not null)"
    " or (kind = 'manual' and project_id is not null and similarity is null"
    " and engine_version is null)"
    " or (kind = 'excluded' and project_id is null and thread_id is null"
    " and similarity is null and engine_version is null)"
)
NEW_SHAPE_CHECK = (
    f"({OLD_SHAPE_CHECK}"
    " or (kind = 'rule' and project_id is not null and similarity is null"
    " and engine_version is null))"
    " and ((kind = 'rule' and rule_condition is not null and rule_value is not null)"
    " or (kind <> 'rule' and rule_condition is null and rule_value is null))"
)


def upgrade() -> None:
    """Apply the change."""
    op.create_table('placement_rules',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('condition', sa.String(length=16), nullable=False),
    sa.Column('value', sa.Text(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('thread_name', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("condition in ('address', 'domain', 'subject')", name=op.f('ck_placement_rules_condition')),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_placement_rules_project_id_projects'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_placement_rules_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_placement_rules'))
    )
    op.create_index('ix_placement_rules_user_id', 'placement_rules', ['user_id'], unique=False)
    op.create_index('uq_placement_rules_user_id_condition_lower_value', 'placement_rules', ['user_id', 'condition', sa.literal_column('lower(value)')], unique=True)
    op.add_column('chain_placements', sa.Column('rule_condition', sa.String(length=16), nullable=True))
    op.add_column('chain_placements', sa.Column('rule_value', sa.Text(), nullable=True))
    op.drop_constraint(op.f('ck_chain_placements_shape'), 'chain_placements', type_='check')
    op.drop_constraint(op.f('ck_chain_placements_kind'), 'chain_placements', type_='check')
    op.create_check_constraint(op.f('ck_chain_placements_kind'), 'chain_placements', "kind in ('engine', 'manual', 'excluded', 'rule')")
    op.create_check_constraint(op.f('ck_chain_placements_shape'), 'chain_placements', NEW_SHAPE_CHECK)


def downgrade() -> None:
    """Revert the change."""
    op.execute("DELETE FROM chain_placements WHERE kind = 'rule'")
    op.drop_constraint(op.f('ck_chain_placements_shape'), 'chain_placements', type_='check')
    op.drop_constraint(op.f('ck_chain_placements_kind'), 'chain_placements', type_='check')
    op.create_check_constraint(op.f('ck_chain_placements_kind'), 'chain_placements', "kind in ('engine', 'manual', 'excluded')")
    op.create_check_constraint(op.f('ck_chain_placements_shape'), 'chain_placements', OLD_SHAPE_CHECK)
    op.drop_column('chain_placements', 'rule_value')
    op.drop_column('chain_placements', 'rule_condition')
    op.drop_index('uq_placement_rules_user_id_condition_lower_value', table_name='placement_rules')
    op.drop_index('ix_placement_rules_user_id', table_name='placement_rules')
    op.drop_table('placement_rules')
