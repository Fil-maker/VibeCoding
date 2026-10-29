"""Personal accounts: drop organizations, invitations, roles and deactivation.

Revision ID: 0003
Revises: 0002
Create Date: 2026-10-28 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op


revision: str = '0003'
down_revision: str | None = '0002'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the change: users, sessions and tokens stay; the organization layer goes."""
    op.drop_index('ix_invitations_organization_id_created_at', table_name='invitations')
    op.drop_table('invitations')
    for table in ('user_tokens', 'sessions', 'users'):
        op.drop_index(op.f(f'ix_{table}_organization_id'), table_name=table)
        op.drop_constraint(
            op.f(f'fk_{table}_organization_id_organizations'), table, type_='foreignkey'
        )
        op.drop_column(table, 'organization_id')
    op.drop_column('users', 'role')
    op.drop_column('users', 'is_active')
    op.drop_table('organizations')


def downgrade() -> None:
    """Revert the change: one organization per user, every user its active administrator."""
    op.create_table('organizations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('name', sa.String(length=200), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_organizations'))
    )
    op.add_column('users', sa.Column('organization_id', sa.Uuid(), nullable=True))
    op.add_column('users', sa.Column('role', sa.String(length=20), nullable=True))
    op.add_column('users', sa.Column('is_active', sa.Boolean(), nullable=True))
    op.execute(
        "UPDATE users SET organization_id = gen_random_uuid(), "
        "role = 'administrator', is_active = true"
    )
    op.execute(
        "INSERT INTO organizations (id, name, created_at) "
        "SELECT organization_id, name, created_at FROM users"
    )
    op.alter_column('users', 'organization_id', nullable=False)
    op.alter_column('users', 'role', nullable=False)
    op.alter_column('users', 'is_active', nullable=False)
    op.create_foreign_key(
        op.f('fk_users_organization_id_organizations'),
        'users', 'organizations', ['organization_id'], ['id'], ondelete='CASCADE',
    )
    op.create_index(op.f('ix_users_organization_id'), 'users', ['organization_id'], unique=False)
    for table in ('sessions', 'user_tokens'):
        op.add_column(table, sa.Column('organization_id', sa.Uuid(), nullable=True))
        op.execute(
            f"UPDATE {table} SET organization_id = users.organization_id "
            f"FROM users WHERE users.id = {table}.user_id"
        )
        op.alter_column(table, 'organization_id', nullable=False)
        op.create_foreign_key(
            op.f(f'fk_{table}_organization_id_organizations'),
            table, 'organizations', ['organization_id'], ['id'], ondelete='CASCADE',
        )
        op.create_index(op.f(f'ix_{table}_organization_id'), table, ['organization_id'], unique=False)
    op.create_table('invitations',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('organization_id', sa.Uuid(), nullable=False),
    sa.Column('email', sa.String(length=254), nullable=False),
    sa.Column('invited_by_user_id', sa.Uuid(), nullable=False),
    sa.Column('token_hash', sa.String(length=64), nullable=False),
    sa.Column('delivery', sa.String(length=20), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('accepted_user_id', sa.Uuid(), nullable=True),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['accepted_user_id'], ['users.id'], name=op.f('fk_invitations_accepted_user_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['invited_by_user_id'], ['users.id'], name=op.f('fk_invitations_invited_by_user_id_users'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['organization_id'], ['organizations.id'], name=op.f('fk_invitations_organization_id_organizations'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_invitations')),
    sa.UniqueConstraint('token_hash', name=op.f('uq_invitations_token_hash'))
    )
    op.create_index('ix_invitations_organization_id_created_at', 'invitations', ['organization_id', 'created_at'], unique=False)
