"""add_m05_2_2_review_and_info_requests

Revision ID: a1b2c3d4e5f6
Revises: d8a9f1b2c3d4
Create Date: 2026-09-21 08:52:00.000000

"""
from typing import Sequence, Union
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, Sequence[str], None] = 'd8a9f1b2c3d4'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Add review tracking columns to documents
    op.add_column('documents', sa.Column('reviewed_by', sa.UUID(), nullable=True))
    op.add_column('documents', sa.Column('reviewed_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('documents', sa.Column('review_notes', sa.String(), nullable=True))
    op.create_foreign_key('fk_documents_reviewed_by_users', 'documents', 'users', ['reviewed_by'], ['id'])

    # 2. Create additional_information_requests table
    op.create_table(
        'additional_information_requests',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('application_id', sa.UUID(), sa.ForeignKey('applications.id'), nullable=False),
        sa.Column('requested_by', sa.UUID(), sa.ForeignKey('users.id'), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('requested_document_type', sa.String(), nullable=True),
        sa.Column('status', sa.String(), nullable=False, server_default='OPEN'),
        sa.Column('response_document_id', sa.UUID(), sa.ForeignKey('documents.id'), nullable=True),
        sa.Column('response_notes', sa.String(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True),
        sa.Column('responded_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('resolved_at', sa.DateTime(timezone=True), nullable=True)
    )
    op.create_index(op.f('ix_additional_information_requests_application_id'), 'additional_information_requests', ['application_id'], unique=False)
    op.create_index(op.f('ix_additional_information_requests_requested_by'), 'additional_information_requests', ['requested_by'], unique=False)

    # 3. Create application_audit_events table
    op.create_table(
        'application_audit_events',
        sa.Column('id', sa.UUID(), primary_key=True, nullable=False),
        sa.Column('application_id', sa.UUID(), sa.ForeignKey('applications.id'), nullable=False),
        sa.Column('user_id', sa.UUID(), sa.ForeignKey('users.id'), nullable=True),
        sa.Column('event_type', sa.String(), nullable=False),
        sa.Column('title', sa.String(), nullable=False),
        sa.Column('description', sa.String(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=True)
    )
    op.create_index(op.f('ix_application_audit_events_application_id'), 'application_audit_events', ['application_id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_application_audit_events_application_id'), table_name='application_audit_events')
    op.drop_table('application_audit_events')
    op.drop_index(op.f('ix_additional_information_requests_requested_by'), table_name='additional_information_requests')
    op.drop_index(op.f('ix_additional_information_requests_application_id'), table_name='additional_information_requests')
    op.drop_table('additional_information_requests')
    op.drop_constraint('fk_documents_reviewed_by_users', 'documents', type_='foreignkey')
    op.drop_column('documents', 'review_notes')
    op.drop_column('documents', 'reviewed_at')
    op.drop_column('documents', 'reviewed_by')
