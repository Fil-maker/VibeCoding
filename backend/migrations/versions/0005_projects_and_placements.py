"""projects and placements

Revision ID: 0005
Revises: 0004
Create Date: 2026-10-29 18:41:12.608251
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0005'
down_revision: str | None = '0004'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the change."""
    op.create_table('projects',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=100), nullable=False),
    sa.Column('description', sa.Text(), nullable=False),
    sa.Column('filled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_projects_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_projects'))
    )
    op.create_index('uq_projects_user_id_lower_name', 'projects', ['user_id', sa.literal_column('lower(name)')], unique=True)
    op.create_table('threads',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_threads_project_id_projects'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_threads_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_threads')),
    sa.UniqueConstraint('project_id', 'position', name=op.f('uq_threads_project_id'))
    )
    op.create_table('chain_placements',
    sa.Column('chain_id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('project_id', sa.Uuid(), nullable=False),
    sa.Column('thread_id', sa.Uuid(), nullable=True),
    sa.Column('kind', sa.String(length=16), nullable=False),
    sa.Column('similarity', sa.Numeric(precision=5, scale=4), nullable=False),
    sa.Column('engine_version', sa.String(length=32), nullable=False),
    sa.Column('placed_at', sa.DateTime(timezone=True), nullable=False),
    sa.CheckConstraint("kind in ('engine')", name=op.f('ck_chain_placements_kind')),
    sa.ForeignKeyConstraint(['chain_id'], ['reply_chains.id'], name=op.f('fk_chain_placements_chain_id_reply_chains'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['project_id'], ['projects.id'], name=op.f('fk_chain_placements_project_id_projects'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['thread_id'], ['threads.id'], name=op.f('fk_chain_placements_thread_id_threads'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_chain_placements_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('chain_id', name=op.f('pk_chain_placements'))
    )
    op.create_index('ix_chain_placements_user_id_project_id', 'chain_placements', ['user_id', 'project_id'], unique=False)


def downgrade() -> None:
    """Revert the change."""
    op.drop_index('ix_chain_placements_user_id_project_id', table_name='chain_placements')
    op.drop_table('chain_placements')
    op.drop_table('threads')
    op.drop_index('uq_projects_user_id_lower_name', table_name='projects')
    op.drop_table('projects')
