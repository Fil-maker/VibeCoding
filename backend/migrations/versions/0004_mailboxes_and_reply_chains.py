"""mailboxes and reply chains

Revision ID: 0004
Revises: 0003
Create Date: 2026-10-29 14:49:30.622169
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = '0004'
down_revision: str | None = '0003'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the change."""
    op.create_table('mailboxes',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('server', sa.String(length=253), nullable=False),
    sa.Column('port', sa.Integer(), nullable=False),
    sa.Column('login', sa.String(length=254), nullable=False),
    sa.Column('password_encrypted', sa.LargeBinary(), nullable=True),
    sa.Column('status', sa.String(length=20), nullable=False),
    sa.Column('error_code', sa.String(length=20), nullable=True),
    sa.Column('read_requested_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_attempt_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('last_read_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('connected_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('disconnected_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_mailboxes_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_mailboxes')),
    sa.UniqueConstraint('user_id', 'server', 'login', name=op.f('uq_mailboxes_user_id'))
    )
    op.create_table('reply_chains',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('latest_email_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_reply_chains_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_reply_chains'))
    )
    op.create_index('ix_reply_chains_user_id_latest_email_at_id', 'reply_chains', ['user_id', sa.literal_column('latest_email_at DESC'), 'id'], unique=False)
    op.create_table('emails',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('user_id', sa.Uuid(), nullable=False),
    sa.Column('chain_id', sa.Uuid(), nullable=False),
    sa.Column('key', sa.String(length=998), nullable=False),
    sa.Column('message_id', sa.String(length=998), nullable=True),
    sa.Column('in_reply_to', sa.String(length=998), nullable=True),
    sa.Column('references', postgresql.ARRAY(sa.Text()), nullable=False),
    sa.Column('subject', sa.Text(), nullable=False),
    sa.Column('from_address', sa.String(length=320), nullable=False),
    sa.Column('from_name', sa.Text(), nullable=True),
    sa.Column('to_addresses', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('cc_addresses', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('sent_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('attachment_names', postgresql.ARRAY(sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
    sa.ForeignKeyConstraint(['chain_id'], ['reply_chains.id'], name=op.f('fk_emails_chain_id_reply_chains'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_emails_user_id_users'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_emails')),
    sa.UniqueConstraint('user_id', 'key', name=op.f('uq_emails_user_id'))
    )
    op.create_index('ix_emails_chain_id_sent_at_id', 'emails', ['chain_id', 'sent_at', 'id'], unique=False)
    op.create_index('ix_emails_references', 'emails', ['references'], unique=False, postgresql_using='gin')
    op.create_index('ix_emails_user_id_in_reply_to', 'emails', ['user_id', 'in_reply_to'], unique=False)
    op.create_table('mailbox_folders',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('mailbox_id', sa.Uuid(), nullable=False),
    sa.Column('kind', sa.String(length=10), nullable=False),
    sa.Column('name', sa.String(length=255), nullable=False),
    sa.Column('uidvalidity', sa.BigInteger(), nullable=True),
    sa.Column('last_uid', sa.BigInteger(), nullable=True),
    sa.ForeignKeyConstraint(['mailbox_id'], ['mailboxes.id'], name=op.f('fk_mailbox_folders_mailbox_id_mailboxes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_mailbox_folders')),
    sa.UniqueConstraint('mailbox_id', 'kind', name=op.f('uq_mailbox_folders_mailbox_id'))
    )
    op.create_table('email_copies',
    sa.Column('id', sa.Uuid(), nullable=False),
    sa.Column('email_id', sa.Uuid(), nullable=False),
    sa.Column('mailbox_id', sa.Uuid(), nullable=False),
    sa.Column('folder_id', sa.Uuid(), nullable=False),
    sa.Column('uid', sa.BigInteger(), nullable=False),
    sa.ForeignKeyConstraint(['email_id'], ['emails.id'], name=op.f('fk_email_copies_email_id_emails'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['folder_id'], ['mailbox_folders.id'], name=op.f('fk_email_copies_folder_id_mailbox_folders'), ondelete='CASCADE'),
    sa.ForeignKeyConstraint(['mailbox_id'], ['mailboxes.id'], name=op.f('fk_email_copies_mailbox_id_mailboxes'), ondelete='CASCADE'),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_email_copies')),
    sa.UniqueConstraint('folder_id', 'uid', name=op.f('uq_email_copies_folder_id'))
    )
    op.create_index(op.f('ix_email_copies_email_id'), 'email_copies', ['email_id'], unique=False)
    op.create_index(op.f('ix_email_copies_mailbox_id'), 'email_copies', ['mailbox_id'], unique=False)


def downgrade() -> None:
    """Revert the change."""
    op.drop_index(op.f('ix_email_copies_mailbox_id'), table_name='email_copies')
    op.drop_index(op.f('ix_email_copies_email_id'), table_name='email_copies')
    op.drop_table('email_copies')
    op.drop_table('mailbox_folders')
    op.drop_index('ix_emails_user_id_in_reply_to', table_name='emails')
    op.drop_index('ix_emails_references', table_name='emails', postgresql_using='gin')
    op.drop_index('ix_emails_chain_id_sent_at_id', table_name='emails')
    op.drop_table('emails')
    op.drop_index('ix_reply_chains_user_id_latest_email_at_id', table_name='reply_chains')
    op.drop_table('reply_chains')
    op.drop_table('mailboxes')
