"""add_m05_3_compliance_workspace

Revision ID: 4d7651d2aa49
Revises: a1b2c3d4e5f6
Create Date: 2026-09-21 13:59:50.448705

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = '4d7651d2aa49'
down_revision: Union[str, Sequence[str], None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema for M05.3 Compliance Workspace."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    # 1. Create compliance_checklist_items table if not exists
    if 'compliance_checklist_items' not in tables:
        op.create_table(
            'compliance_checklist_items',
            sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
            sa.Column('application_id', sa.UUID(), sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False),
            sa.Column('item_key', sa.String(), nullable=False),
            sa.Column('category', sa.String(), nullable=False),
            sa.Column('title', sa.String(), nullable=False),
            sa.Column('description', sa.String(), nullable=True),
            sa.Column('status', sa.String(), nullable=False, server_default='PENDING'),
            sa.Column('notes', sa.String(), nullable=True),
            sa.Column('display_order', sa.Integer(), nullable=False, server_default='0'),
            sa.Column('updated_by', sa.UUID(), sa.ForeignKey('users.id', ondelete='SET NULL'), nullable=True),
            sa.Column('updated_at', sa.DateTime(timezone=True), nullable=True),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
        )
        op.create_index(
            op.f('ix_compliance_checklist_items_application_id'),
            'compliance_checklist_items',
            ['application_id'],
            unique=False
        )
    else:
        # Development safe: Ensure index exists if table already present
        indexes = [ix['name'] for ix in inspector.get_indexes('compliance_checklist_items')]
        if 'ix_compliance_checklist_items_application_id' not in indexes:
            op.create_index(
                op.f('ix_compliance_checklist_items_application_id'),
                'compliance_checklist_items',
                ['application_id'],
                unique=False
            )

    # 2. Create compliance_review_notes table if not exists
    if 'compliance_review_notes' not in tables:
        op.create_table(
            'compliance_review_notes',
            sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
            sa.Column('application_id', sa.UUID(), sa.ForeignKey('applications.id', ondelete='CASCADE'), nullable=False),
            sa.Column('author_id', sa.UUID(), sa.ForeignKey('users.id', ondelete='CASCADE'), nullable=False),
            sa.Column('note', sa.String(), nullable=False),
            sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
        )
        op.create_index(
            op.f('ix_compliance_review_notes_application_id'),
            'compliance_review_notes',
            ['application_id'],
            unique=False
        )
        op.create_index(
            op.f('ix_compliance_review_notes_author_id'),
            'compliance_review_notes',
            ['author_id'],
            unique=False
        )
    else:
        # Development safe: Ensure indexes exist if table already present
        indexes = [ix['name'] for ix in inspector.get_indexes('compliance_review_notes')]
        if 'ix_compliance_review_notes_application_id' not in indexes:
            op.create_index(
                op.f('ix_compliance_review_notes_application_id'),
                'compliance_review_notes',
                ['application_id'],
                unique=False
            )
        if 'ix_compliance_review_notes_author_id' not in indexes:
            op.create_index(
                op.f('ix_compliance_review_notes_author_id'),
                'compliance_review_notes',
                ['author_id'],
                unique=False
            )


def downgrade() -> None:
    """Downgrade schema for M05.3 Compliance Workspace."""
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = inspector.get_table_names()

    if 'compliance_review_notes' in tables:
        indexes = [ix['name'] for ix in inspector.get_indexes('compliance_review_notes')]
        if 'ix_compliance_review_notes_author_id' in indexes:
            op.drop_index(op.f('ix_compliance_review_notes_author_id'), table_name='compliance_review_notes')
        if 'ix_compliance_review_notes_application_id' in indexes:
            op.drop_index(op.f('ix_compliance_review_notes_application_id'), table_name='compliance_review_notes')
        op.drop_table('compliance_review_notes')

    if 'compliance_checklist_items' in tables:
        indexes = [ix['name'] for ix in inspector.get_indexes('compliance_checklist_items')]
        if 'ix_compliance_checklist_items_application_id' in indexes:
            op.drop_index(op.f('ix_compliance_checklist_items_application_id'), table_name='compliance_checklist_items')
        op.drop_table('compliance_checklist_items')
