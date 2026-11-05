"""email attachments with sizes

Revision ID: 0009
Revises: 0008
Create Date: 2026-11-05 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql


revision: str = '0009'
down_revision: str | None = '0008'
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Apply the change."""
    op.add_column(
        'emails',
        sa.Column('attachments', postgresql.JSONB(astext_type=sa.Text()), nullable=False, server_default='[]'),
    )
    op.execute(
        "UPDATE emails SET attachments = COALESCE(("
        "SELECT jsonb_agg(jsonb_build_object('name', name, 'size', NULL) ORDER BY position) "
        "FROM unnest(attachment_names) WITH ORDINALITY AS item(name, position)), '[]'::jsonb)"
    )
    op.alter_column('emails', 'attachments', server_default=None)
    op.drop_column('emails', 'attachment_names')


def downgrade() -> None:
    """Revert the change."""
    op.add_column(
        'emails',
        sa.Column('attachment_names', postgresql.ARRAY(sa.Text()), nullable=False, server_default='{}'),
    )
    op.execute(
        "UPDATE emails SET attachment_names = COALESCE(("
        "SELECT array_agg(item.value ->> 'name' ORDER BY item.position) "
        "FROM jsonb_array_elements(attachments) WITH ORDINALITY AS item(value, position)), '{}')"
    )
    op.alter_column('emails', 'attachment_names', server_default=None)
    op.drop_column('emails', 'attachments')
